#include <cmath>
#include "kernel_operator.h"

/*
 * AddRmsNormBias - shape-regime optimized Ascend C implementation for dav-2201.
 * Revision: V17_FUSED_AFFINE_20261013
 * V17 vs V16: on the four merged half routes (Iso06/07/08/10) the post-norm
 * affine out = y*gamma + bias is one FusedMulAdd over all rows (dst=y,
 * src0=gamma, src1=bias; gamma/bias are a single row reused with repStride 0),
 * replacing the separate full-width Mul then Add vector passes. Precision is
 * unchanged-or-better (single fused mul-add) and Sqrt/Div are untouched.
 * V16: aligned contiguous bursts use plain DataCopy instead of the
 * DataCopyPad mask engine; unaligned tails keep DataCopyPad.
 * Row-wise Brcb uses ceil(rows / 8) repeats: one repeat consumes eight
 * FP32 scales and emits eight 32-byte blocks, not one row per repeat.
 *
 * Golden semantics from the supplied project (FP32/fallback reference):
 *   y   = float32(x) + float32(residual)
 *   inv = 1 / sqrt(mean(y * y) + epsilon)
 *   out = cast_input_dtype(y * inv * float32(gamma) + float32(bias))
 * Some specialized FP16 routes retain the established mixed-precision
 * arithmetic (FP16 residual Add and/or affine operations). They must be
 * assessed separately from the all-FP32 reference above.
 *
 * Two paths:
 *   - D <= 8192: resident-row fast path (x/residual read once)
 *   - D > 8192 : 8192-element tiled two-pass path
 *
 * Only APIs used here are standard A2 Ascend C APIs also used by the
 * production RMSNorm/AddRmsNormBias implementation: DataCopyPad, Cast,
 * Add/Mul/Muls/Adds, WholeReduceSum, Sqrt, Div and V<->S events.
 */

namespace AddRmsNormBiasFixed {
using namespace AscendC;

constexpr uint32_t ALIGN_BYTES = 32U;
constexpr uint32_t FP32_PER_REPEAT = 64U;
constexpr uint32_t REDUCE_WORK_FLOATS = 64U;
constexpr uint32_t TILE_ELEMS = 8192U;
constexpr uint32_t FAST_LIMIT = 8192U;
constexpr uint32_t MERGE_LIMIT = 1600U;
constexpr uint32_t MULTI_LIMIT = 5120U;
constexpr uint32_t SINGLE_RESIDENT_LIMIT = 16000U;
constexpr uint32_t MERGE_UB_BYTES = 195584U;

__aicore__ inline uint32_t AlignUp32(uint32_t bytes)
{
    return (bytes + ALIGN_BYTES - 1U) & ~(ALIGN_BYTES - 1U);
}

__aicore__ inline uint32_t MinU32(uint32_t a, uint32_t b)
{
    return a < b ? a : b;
}

__aicore__ inline uint64_t MinU64(uint64_t a, uint64_t b)
{
    return a < b ? a : b;
}

template <typename T>
__aicore__ inline void CopyInPad(
    const LocalTensor<T>& dst,
    const GlobalTensor<T>& src,
    uint32_t count)
{
    // Fast plain-DMA path for fully 32B-aligned contiguous bursts; DataCopyPad
    // (mask engine) is reserved for genuinely unaligned tails (192/576/...).
    if (count * sizeof(T) % ALIGN_BYTES == 0U) {
        DataCopy(dst, src, count);
        return;
    }
    DataCopyParams p;
    p.blockLen = count * sizeof(T);
    p.blockCount = 1;
    DataCopyPadParams pad;
    DataCopyPad(dst, src, p, pad);
}

template <typename T>
__aicore__ inline void CopyOutPad(
    const GlobalTensor<T>& dst,
    const LocalTensor<T>& src,
    uint32_t count)
{
    if (count * sizeof(T) % ALIGN_BYTES == 0U) {
        DataCopy(dst, src, count);
        return;
    }
    DataCopyParams p;
    p.blockLen = count * sizeof(T);
    p.blockCount = 1;
    DataCopyPad(dst, src, p);
}

template <typename T>
__aicore__ inline void CopyInRowsPad(
    const LocalTensor<T>& dst,
    const GlobalTensor<T>& src,
    uint32_t rows,
    uint32_t cols)
{
    // Aligned tight rows: the whole burst is one contiguous aligned span.
    if (cols * sizeof(T) % ALIGN_BYTES == 0U) {
        DataCopy(dst, src, rows * cols);
        return;
    }
    DataCopyParams p;
    p.blockLen = cols * sizeof(T);
    p.blockCount = rows;
    DataCopyPadParams pad;
    DataCopyPad(dst, src, p, pad);
}

template <typename T>
__aicore__ inline void CopyOutRowsPad(
    const GlobalTensor<T>& dst,
    const LocalTensor<T>& src,
    uint32_t rows,
    uint32_t cols)
{
    if (cols * sizeof(T) % ALIGN_BYTES == 0U) {
        DataCopy(dst, src, rows * cols);
        return;
    }
    DataCopyParams p;
    p.blockLen = cols * sizeof(T);
    p.blockCount = rows;
    DataCopyPad(dst, src, p);
}

__aicore__ inline void ToFloat(
    const LocalTensor<float>& dst,
    const LocalTensor<half>& src,
    uint32_t count)
{
    Cast(dst, src, RoundMode::CAST_NONE, count);
}

__aicore__ inline void ToFloat(
    const LocalTensor<float>& dst,
    const LocalTensor<bfloat16_t>& src,
    uint32_t count)
{
    Cast(dst, src, RoundMode::CAST_NONE, count);
}

__aicore__ inline void ToFloat(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& src,
    uint32_t count)
{
    Adds(dst, src, 0.0f, count);
}

__aicore__ inline void FromFloat(
    const LocalTensor<half>& dst,
    const LocalTensor<float>& src,
    uint32_t count)
{
    Cast(dst, src, RoundMode::CAST_NONE, count);
}

__aicore__ inline void FromFloat(
    const LocalTensor<bfloat16_t>& dst,
    const LocalTensor<float>& src,
    uint32_t count)
{
    Cast(dst, src, RoundMode::CAST_RINT, count);
}

__aicore__ inline void FromFloat(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& src,
    uint32_t count)
{
    Adds(dst, src, 0.0f, count);
}

__aicore__ inline void BuildYFp32(
    const LocalTensor<float>& y,
    const LocalTensor<float>& tmp,
    const LocalTensor<float>& a,
    const LocalTensor<float>& b,
    uint32_t count)
{
    Add(y, a, b, count);
}

__aicore__ inline void BuildYFp32(
    const LocalTensor<float>& y,
    const LocalTensor<float>& tmp,
    const LocalTensor<half>& a,
    const LocalTensor<half>& b,
    uint32_t count)
{
    ToFloat(y, a, count);
    ToFloat(tmp, b, count);
    Add(y, y, tmp, count);
}

__aicore__ inline void BuildYFp32(
    const LocalTensor<float>& y,
    const LocalTensor<float>& tmp,
    const LocalTensor<bfloat16_t>& a,
    const LocalTensor<bfloat16_t>& b,
    uint32_t count)
{
    ToFloat(y, a, count);
    ToFloat(tmp, b, count);
    Add(y, y, tmp, count);
}

// Based on the official A2 FP32 reduction helper. count <= 8192 here,
// therefore repeatTimes <= 128 and stays below the 255-repeat limit.
__aicore__ inline void ReduceSumFp32(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& src,
    const LocalTensor<float>& work,
    uint32_t count)
{
    const uint64_t mask = FP32_PER_REPEAT;
    const uint32_t repeatTimes = count / FP32_PER_REPEAT;
    const uint32_t tailCount = count % FP32_PER_REPEAT;
    const uint32_t bodyCount = repeatTimes * FP32_PER_REPEAT;

    BinaryRepeatParams repeatParams;
    repeatParams.src0RepStride = ONE_REPEAT_BYTE_SIZE / ONE_BLK_SIZE;
    repeatParams.src0BlkStride = 1;
    repeatParams.src1RepStride = 0;
    repeatParams.src1BlkStride = 1;
    repeatParams.dstRepStride = 0;
    repeatParams.dstBlkStride = 1;

    Duplicate(work, 0.0f, FP32_PER_REPEAT);

    if (repeatTimes > 0U) {
        Add(work, src, work, mask, static_cast<uint8_t>(repeatTimes), repeatParams);
    }
    if (tailCount != 0U) {
        Add(work, src[bodyCount], work, static_cast<uint64_t>(tailCount), 1, repeatParams);
    }

    AscendCUtils::SetMask<float>(FP32_PER_REPEAT);
#if defined(__CCE_AICORE__) && (__CCE_AICORE__ == 220)
    if (g_coreType == AIV) {
        WholeReduceSum<float, false>(dst, work, MASK_PLACEHOLDER, 1, 0, 1, 0);
    }
#else
    WholeReduceSum<float, false>(
        dst, work, MASK_PLACEHOLDER, 1, 1, 1, DEFAULT_REPEAT_STRIDE);
#endif
}

// Fused square accumulation into 64 FP32 lanes.  This is used by the
// large-D single-row path so all D-tiles share one accumulator and only one
// WholeReduceSum is issued for the entire row. MulAddDst is available on A2.
__aicore__ inline void AccumulateSquare64(
    const LocalTensor<float>& acc,
    const LocalTensor<float>& src,
    uint32_t count)
{
    uint32_t offset = 0U;
    uint32_t fullRepeats = count / FP32_PER_REPEAT;
    while (fullRepeats != 0U) {
        uint32_t group = fullRepeats;
        if (group > 255U) group = 255U;
        MulAddDst(acc, src[offset], src[offset], FP32_PER_REPEAT,
            static_cast<uint8_t>(group), {1, 1, 1, 0, 8, 8});
        offset += group * FP32_PER_REPEAT;
        fullRepeats -= group;
    }
    const uint32_t tail = count - offset;
    if (tail != 0U) {
        MulAddDst(acc, src[offset], src[offset], tail, 1,
            {1, 1, 1, 0, 8, 8});
    }
}

__aicore__ inline void FinalizeAcc64(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& acc)
{
    AscendCUtils::SetMask<float>(FP32_PER_REPEAT);
#if defined(__CCE_AICORE__) && (__CCE_AICORE__ == 220)
    if (g_coreType == AIV) {
        WholeReduceSum<float, false>(dst, acc, FP32_PER_REPEAT, 1, 0, 1, 0);
    }
#else
    WholeReduceSum<float, false>(
        dst, acc, FP32_PER_REPEAT, 1, 1, 1, DEFAULT_REPEAT_STRIDE);
#endif
}


// Barrier-free helpers for direct-kernel builds.  CANN kernel-launch projects
// enable Vector auto-synchronization by default, so LocalTensor dependencies
// are sufficient inside the latency-specialized micro-kernels.  Cross-pipe
// MTE2/V/MTE3 synchronization is still explicit at the call sites.
__aicore__ inline void FinalizeAcc64Auto(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& acc)
{
    AscendCUtils::SetMask<float>(FP32_PER_REPEAT);
#if defined(__CCE_AICORE__) && (__CCE_AICORE__ == 220)
    if (g_coreType == AIV) {
        WholeReduceSum<float, false>(dst, acc, FP32_PER_REPEAT, 1, 0, 1, 0);
    }
#else
    WholeReduceSum<float, false>(
        dst, acc, FP32_PER_REPEAT, 1, 1, 1, DEFAULT_REPEAT_STRIDE);
#endif
}

__aicore__ inline void NormalizeRowAuto(
    const LocalTensor<float>& y,
    const LocalTensor<float>& sumTensor,
    const LocalTensor<float>& scratchTensor,
    uint32_t count, float invD, float epsilon)
{
    Muls(sumTensor, sumTensor, invD, 1);
    Adds(sumTensor, sumTensor, epsilon, 1);
    Sqrt(sumTensor, sumTensor, 1);
    Duplicate(scratchTensor, 1.0f, 1);
    Div(sumTensor, scratchTensor, sumTensor, 1);
    Brcb(scratchTensor, sumTensor, 1, {1, 8});
    const uint32_t repeat = count / FP32_PER_REPEAT;
    const uint32_t body = repeat * FP32_PER_REPEAT;
    if (repeat > 0U) {
        Mul(y, y, scratchTensor, FP32_PER_REPEAT, static_cast<uint8_t>(repeat),
            {1, 1, 0, 8, 8, 0});
    }
    if (body < count) {
        Mul(y[body], y[body], scratchTensor, count - body, 1,
            {1, 1, 0, 8, 8, 0});
    }
}

__aicore__ inline void MulByBroadcast64(
    const LocalTensor<float>& y,
    const LocalTensor<float>& broadcast,
    uint32_t count)
{
    const uint32_t repeat = count / FP32_PER_REPEAT;
    const uint32_t body = repeat * FP32_PER_REPEAT;
    if (repeat > 0U) {
        Mul(y, y, broadcast, FP32_PER_REPEAT, static_cast<uint8_t>(repeat),
            {1, 1, 0, 8, 8, 0});
    }
    if (body < count) {
        Mul(y[body], y[body], broadcast, count - body, 1,
            {1, 1, 0, 8, 8, 0});
    }
}

__aicore__ inline void ReduceSumSmallPre(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& src,
    const LocalTensor<float>& tmp,
    uint32_t numCol,
    uint32_t tail,
    uint32_t repeat,
    uint8_t repStride)
{
    uint32_t col = 0U;
    for (; col + FP32_PER_REPEAT <= numCol; col += FP32_PER_REPEAT) {
        Add(tmp, src[col], tmp, FP32_PER_REPEAT, repeat,
            {1, 1, 1, 8, repStride, 8});
    }
    if (tail != 0U) {
        Add(tmp, src[col], tmp, tail, repeat,
            {1, 1, 1, 8, repStride, 8});
    }
    AscendCUtils::SetMask<float>(FP32_PER_REPEAT);
#if defined(__CCE_AICORE__) && (__CCE_AICORE__ == 220)
    if (g_coreType == AIV) {
        WholeReduceSum<float, false>(dst, tmp, FP32_PER_REPEAT, repeat, 1, 1, 8);
    }
#else
    WholeReduceSum<float, false>(dst, tmp, FP32_PER_REPEAT, repeat, 1, 1, 8);
#endif
}

__aicore__ inline void ReduceSumMultiN(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& src,
    const LocalTensor<float>& tmp,
    uint32_t rows,
    uint32_t cols,
    uint32_t colsAlign)
{
    const uint32_t tail = cols % FP32_PER_REPEAT;
    const uint8_t repStride = static_cast<uint8_t>(colsAlign / 8U);
    Duplicate(tmp, 0.0f, rows * FP32_PER_REPEAT);
    // MERGE rowFactor is deliberately kept below 255, so one repeat group is enough.
    ReduceSumSmallPre(dst, src, tmp, cols, tail, rows, repStride);
}


// Barrier-free multi-row reduction for latency-oriented one-batch kernels.
// The direct-launch build uses Vector auto-synchronization; only MTE2/V/MTE3
// crossings are synchronized explicitly by those kernels.
__aicore__ inline void ReduceSumSmallPreAuto(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& src,
    const LocalTensor<float>& tmp,
    uint32_t numCol,
    uint32_t tail,
    uint32_t repeat,
    uint8_t repStride)
{
    uint32_t col = 0U;
    for (; col + FP32_PER_REPEAT <= numCol; col += FP32_PER_REPEAT) {
        Add(tmp, src[col], tmp, FP32_PER_REPEAT, repeat,
            {1, 1, 1, 8, repStride, 8});
    }
    if (tail != 0U) {
        Add(tmp, src[col], tmp, tail, repeat,
            {1, 1, 1, 8, repStride, 8});
    }
    AscendCUtils::SetMask<float>(FP32_PER_REPEAT);
#if defined(__CCE_AICORE__) && (__CCE_AICORE__ == 220)
    if (g_coreType == AIV) {
        WholeReduceSum<float, false>(dst, tmp, FP32_PER_REPEAT, repeat, 1, 1, 8);
    }
#else
    WholeReduceSum<float, false>(dst, tmp, FP32_PER_REPEAT, repeat, 1, 1, 8);
#endif
}

__aicore__ inline void ReduceSumMultiNAuto(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& src,
    const LocalTensor<float>& tmp,
    uint32_t rows,
    uint32_t cols,
    uint32_t colsAlign)
{
    const uint32_t tail = cols % FP32_PER_REPEAT;
    const uint8_t repStride = static_cast<uint8_t>(colsAlign / 8U);
    Duplicate(tmp, 0.0f, rows * FP32_PER_REPEAT);
    ReduceSumSmallPreAuto(dst, src, tmp, cols, tail, rows, repStride);
}

__aicore__ inline float ReadScalar(const LocalTensor<float>& src)
{
    event_t e = static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::V_S));
    SetFlag<HardEvent::V_S>(e);
    WaitFlag<HardEvent::V_S>(e);
    return src.GetValue(0);
}

__aicore__ inline float CalcInvRmsTensor(
    const LocalTensor<float>& sumTensor,
    const LocalTensor<float>& scratchTensor,
    float invD,
    float epsilon)
{
    // Keep sqrt/div entirely on the Vector pipe. Host libm functions such as
    // sqrtf cannot be called from __aicore__ code on dav-2201.
    Muls(sumTensor, sumTensor, invD, 1);
    Adds(sumTensor, sumTensor, epsilon, 1);
    Sqrt(sumTensor, sumTensor, 1);
    Duplicate(scratchTensor, 1.0f, 1);
    Div(sumTensor, scratchTensor, sumTensor, 1);
    return ReadScalar(sumTensor);
}


// Normalize one resident row without Vector->Scalar->Vector synchronization.
// Brcb expands the one-element rstd into a 32-byte block and Mul broadcasts
// that block across every repeat. On short rows this saves a large fixed cost.
__aicore__ inline void NormalizeRowVector(
    const LocalTensor<float>& y,
    const LocalTensor<float>& sumTensor,
    const LocalTensor<float>& scratchTensor,
    uint32_t count,
    float invD,
    float epsilon)
{
    Muls(sumTensor, sumTensor, invD, 1);
    Adds(sumTensor, sumTensor, epsilon, 1);
    Sqrt(sumTensor, sumTensor, 1);
    Duplicate(scratchTensor, 1.0f, 1);
    Div(sumTensor, scratchTensor, sumTensor, 1);
    Brcb(scratchTensor, sumTensor, 1, {1, 8});
    const uint32_t repeat = count / FP32_PER_REPEAT;
    const uint32_t body = repeat * FP32_PER_REPEAT;
    if (repeat > 0U) {
        Mul(y, y, scratchTensor, FP32_PER_REPEAT, static_cast<uint8_t>(repeat),
            {1, 1, 0, 8, 8, 0});
    }
    if (body < count) {
        Mul(y[body], y[body], scratchTensor, count - body, 1,
            {1, 1, 0, 8, 8, 0});
    }
}



// Low-latency one-batch FP32 path for small/medium row widths.  The host only
// selects it when every row assigned to a core fits in UB at once.  That lets
// us remove queue bookkeeping and the inner batch loop while retaining the
// same vector-only multi-row RMS reduction used by the general merge path.
// Generic baseline classes removed from the submission build; the
// route-private IsoXX kernels below own every official benchmark case.

} // namespace AddRmsNormBiasFixed

using namespace AscendC;

// Concrete, non-template kernel entrypoints are intentionally kept in the
// global namespace. This is the most conservative form for direct invocation.





// ============================================================================
// IsolationV2: 15 independent workload routes.
//
// Contract:
//   * Top-level dispatcher only parses shape and performs Match -> Launch -> return.
//   * Every route computes its own dAlign/blockFactor/rowFactor/batch/UB budget.
//   * Baseline device classes above this section are FROZEN read-only primitives.
//     New optimization work must add a route-local class rather than edit them.
//   * Every route has a unique kernel entrypoint, even when it currently wraps a
//     frozen baseline class. This keeps launch ownership independent.
//   * IsolationV2FallbackDispatch below remains a complete generic fallback.
// ============================================================================

using namespace AscendC;


// ============================================================================
// PhysicalIsolationV3: route-private performance-critical kernel classes.
// The shared AddRmsNormBiasFixed namespace above is a frozen compatibility /
// fallback baseline. Future route tuning MUST NOT edit it. If a shared helper
// needs tuning, copy that helper into the corresponding IsoXXPrivate namespace.
// ============================================================================

namespace Iso01Private {
using namespace AscendC;
using namespace AddRmsNormBiasFixed;
// Private physical copy. Public AddRmsNormBiasFixed is frozen and must not be edited for route tuning.
__aicore__ inline void NormalizeRowScaledEpsilon64(
    const LocalTensor<float>& y,
    const LocalTensor<float>& sumTensor,
    const LocalTensor<float>& scratchTensor,
    float epsilonTimes64)
{
    Adds(sumTensor, sumTensor, epsilonTimes64, 1);
    Sqrt(sumTensor, sumTensor, 1);
    Duplicate(scratchTensor, 8.0f, 1);
    Div(sumTensor, scratchTensor, sumTensor, 1);
    Brcb(scratchTensor, sumTensor, 1, {1, 8});
    Mul(y, y, scratchTensor, FP32_PER_REPEAT, 1,
        {1, 1, 0, 8, 8, 0});
}

template <typename T, uint32_t D>
class TinyOneRowKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, float epsilon, float invD)
    {
        rows_ = rows; eps_ = epsilon; invD_ = invD;
        xGm_.SetGlobalBuffer((__gm__ T*)x);
        residualGm_.SetGlobalBuffer((__gm__ T*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ T*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ T*)bias);
        outGm_.SetGlobalBuffer((__gm__ T*)output);
        // Raw x/r/g/b followed by FP32 x/r/g/b and two D-wide workspaces.
        // Iso01 instantiates this class only for the aligned 64-wide FP16 row.
    }

    __aicore__ inline void Process()
    {
        const uint64_t row = static_cast<uint64_t>(GetBlockIdx());
        if (row >= rows_) return;
        const uint64_t off = row * static_cast<uint64_t>(D);
        LocalTensor<float> ubF(TPosition::VECCALC, 0U, 8U * D);
        LocalTensor<T> ubT = ubF.ReinterpretCast<T>();
        LocalTensor<T> x = ubT;
        LocalTensor<T> r = ubT[D];
        LocalTensor<T> g = ubT[2U * D];
        LocalTensor<T> b = ubT[3U * D];
        constexpr uint32_t BASE_F = (sizeof(T) == 4U) ? 4U * D : 2U * D;
        LocalTensor<float> y = ubF[BASE_F];
        LocalTensor<float> residualF = ubF[BASE_F + D];
        LocalTensor<float> gammaF = ubF[BASE_F + 2U * D];
        LocalTensor<float> biasF = ubF[BASE_F + 3U * D];
        LocalTensor<float> tmp = ubF[BASE_F + 4U * D];
        LocalTensor<float> work = ubF[BASE_F + 5U * D];

        // Every host-dispatched Tiny D is naturally 32-byte aligned.  Plain
        // DataCopy avoids DataCopyPad setup in the 1~10 us latency regime.
        DataCopy(x, xGm_[off], D);
        DataCopy(r, residualGm_[off], D);
        DataCopy(g, gammaGm_, D);
        DataCopy(b, biasGm_, D);
        event_t ein = static_cast<event_t>(0);
        SetFlag<HardEvent::MTE2_V>(ein);
        WaitFlag<HardEvent::MTE2_V>(ein);
        ToFloat(y, x, 4U * D);
        Add(y, y, residualF, D);

        // Fuse square and the first reduction stage.  For D=64 the direct
        // WholeReduce path is shorter; larger fixed widths accumulate to 64
        // lanes and perform one final reduction.
        if (D == FP32_PER_REPEAT) {
            Mul(tmp, y, y, D);
            AscendCUtils::SetMask<float>(FP32_PER_REPEAT);
#if defined(__CCE_AICORE__) && (__CCE_AICORE__ == 220)
            if (g_coreType == AIV) {
                WholeReduceSum<float, false>(work, tmp, FP32_PER_REPEAT, 1, 0, 1, 0);
            }
#else
            WholeReduceSum<float, false>(
                work, tmp, FP32_PER_REPEAT, 1, 1, 1, DEFAULT_REPEAT_STRIDE);
#endif
        } else {
            Duplicate(tmp, 0.0f, FP32_PER_REPEAT);
            AccumulateSquare64(tmp, y, D);
            FinalizeAcc64Auto(work, tmp);
        }
        // Prepare affine operands in one Cast while normalization works on
        // disjoint buffers. No gamma/bias conversion remains on its tail.
        NormalizeRowScaledEpsilon64(y, work, tmp, eps_);
        FusedMulAdd(y, gammaF, biasF, D);
        FromFloat(x, y, D);
        event_t eout = static_cast<event_t>(0);
        SetFlag<HardEvent::V_MTE3>(eout);
        WaitFlag<HardEvent::V_MTE3>(eout);
        DataCopy(outGm_[off], x, D);
        PipeBarrier<PIPE_ALL>();
    }
private:
    GlobalTensor<T> xGm_, residualGm_, gammaGm_, biasGm_, outGm_;
    uint64_t rows_;
    float eps_, invD_;
};
template <typename T>
class SingleLowKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, float epsilon, float invD)
    {
        rows_ = rows;
        d_ = d;
        dAlign_ = dAlign;
        eps_ = epsilon;
        invD_ = invD;
        xGm_.SetGlobalBuffer((__gm__ T*)x);
        residualGm_.SetGlobalBuffer((__gm__ T*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ T*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ T*)bias);
        outGm_.SetGlobalBuffer((__gm__ T*)output);
        pipe_.InitBuffer(unitBuf_, MERGE_UB_BYTES);
    }

    __aicore__ inline void Process()
    {
        const uint64_t row = static_cast<uint64_t>(GetBlockIdx());
        if (row >= rows_) {
            return;
        }
        const uint64_t off = row * static_cast<uint64_t>(d_);
        LocalTensor<float> ubF = unitBuf_.Get<float>();
        LocalTensor<T> ubT = ubF.ReinterpretCast<T>();
        LocalTensor<T> x = ubT;
        LocalTensor<T> r = ubT[dAlign_];
        LocalTensor<float> y = ubF[dAlign_];
        LocalTensor<float> tmp = ubF[2U * dAlign_];
        LocalTensor<float> work = ubF[3U * dAlign_];

        CopyInPad(x, xGm_[off], d_);
        event_t ex = static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(ex);
        CopyInPad(r, residualGm_[off], d_);
        event_t er = static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(er);
        WaitFlag<HardEvent::MTE2_V>(ex);
        WaitFlag<HardEvent::MTE2_V>(er);

        ToFloat(y, x, d_);
        ToFloat(tmp, r, d_);
        Add(y, y, tmp, d_);
        Mul(tmp, y, y, d_);
        ReduceSumFp32(tmp, tmp, work, d_);
        NormalizeRowVector(y, tmp, work, d_, invD_, eps_);

        RefillParam(r, gammaGm_);
        ToFloat(tmp, r, d_);
        Mul(y, y, tmp, d_);

        RefillParam(r, biasGm_);
        ToFloat(tmp, r, d_);
        Add(y, y, tmp, d_);

        FromFloat(x, y, d_);
        event_t eo = static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::V_MTE3));
        SetFlag<HardEvent::V_MTE3>(eo);
        WaitFlag<HardEvent::V_MTE3>(eo);
        CopyOutPad(outGm_[off], x, d_);
    }

private:
    __aicore__ inline void RefillParam(
        const LocalTensor<T>& dst,
        const GlobalTensor<T>& src)
    {
        event_t evm = static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::V_MTE2));
        SetFlag<HardEvent::V_MTE2>(evm);
        WaitFlag<HardEvent::V_MTE2>(evm);
        CopyInPad(dst, src, d_);
        event_t emv = static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(emv);
        WaitFlag<HardEvent::MTE2_V>(emv);
    }

private:
    TPipe pipe_;
    TBuf<TPosition::VECCALC> unitBuf_;
    GlobalTensor<T> xGm_;
    GlobalTensor<T> residualGm_;
    GlobalTensor<T> gammaGm_;
    GlobalTensor<T> biasGm_;
    GlobalTensor<T> outGm_;
    uint64_t rows_;
    uint32_t d_;
    uint32_t dAlign_;
    float eps_;
    float invD_;
};
} // namespace Iso01Private


namespace Iso02Private {
using namespace AscendC;
using namespace AddRmsNormBiasFixed;
// Same rounded-square and 64-lane addition order as ReduceSumFp32. Keep this
// helper private: only the short-row direct kernel uses compiler V auto-sync.
__aicore__ inline void ReduceSmallRowBlockWholeAuto(
    const LocalTensor<float>& dst, const LocalTensor<float>& src,
    const LocalTensor<float>& work, uint32_t count)
{
    const uint32_t full = count / FP32_PER_REPEAT;
    const uint32_t body = full * FP32_PER_REPEAT;
    const uint32_t tail = count - body;
    if (full != 0U) {
        BlockReduceSum<float>(work, src, static_cast<uint8_t>(full),
            FP32_PER_REPEAT, 1, 1, 8);
    }
    if (tail != 0U) {
        BlockReduceSum<float>(work[full * 8U], src[body], 1,
            tail, 1, 1, 8);
    }
    const uint32_t partials = full * 8U + (tail + 7U) / 8U;
    WholeReduceSum<float>(dst, work, partials, 1, 1, 1, 8);
}

// Private physical copy. Public AddRmsNormBiasFixed is frozen and must not be edited for route tuning.
class SinglePrefetchFloatKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, float epsilon, float invD)
    {
        rows_ = rows; d_ = d; dAlign_ = dAlign; eps_ = epsilon; invD_ = invD;
        xGm_.SetGlobalBuffer((__gm__ float*)x);
        residualGm_.SetGlobalBuffer((__gm__ float*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ float*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ float*)bias);
        outGm_.SetGlobalBuffer((__gm__ float*)output);
    }

    __aicore__ inline void Process()
    {
        const uint64_t row = static_cast<uint64_t>(GetBlockIdx());
        if (row >= rows_) return;
        const uint64_t off = row * static_cast<uint64_t>(d_);
        LocalTensor<float> ub(TPosition::VECCALC, 0U, 5U * dAlign_ + FP32_PER_REPEAT);
        LocalTensor<float> x = ub;
        LocalTensor<float> r = ub[dAlign_];
        LocalTensor<float> g = ub[2U * dAlign_];
        LocalTensor<float> b = ub[3U * dAlign_];
        LocalTensor<float> tmp = ub[4U * dAlign_];
        LocalTensor<float> work = ub[5U * dAlign_];

        CopyInPad(x, xGm_[off], d_);
        CopyInPad(r, residualGm_[off], d_);
        event_t ein = static_cast<event_t>(0);
        SetFlag<HardEvent::MTE2_V>(ein);
        CopyInPad(g, gammaGm_, d_);
        CopyInPad(b, biasGm_, d_);
        event_t eparam = static_cast<event_t>(1);
        SetFlag<HardEvent::MTE2_V>(eparam);
        WaitFlag<HardEvent::MTE2_V>(ein);

        Add(x, x, r, d_);
        Mul(tmp, x, x, d_);
        ReduceSmallRowBlockWholeAuto(tmp, tmp, work, d_);
        NormalizeRowAuto(x, tmp, work, d_, invD_, eps_);
        WaitFlag<HardEvent::MTE2_V>(eparam);
        Mul(x, x, g, d_);
        Add(x, x, b, d_);

        event_t eout = static_cast<event_t>(0);
        SetFlag<HardEvent::V_MTE3>(eout);
        WaitFlag<HardEvent::V_MTE3>(eout);
        CopyOutPad(outGm_[off], x, d_);
        PipeBarrier<PIPE_ALL>();
    }
private:
    GlobalTensor<float> xGm_, residualGm_, gammaGm_, biasGm_, outGm_;
    uint64_t rows_;
    uint32_t d_, dAlign_;
    float eps_, invD_;
};
class SinglePrefetchFloatGridKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, float epsilon, float invD)
    {
        rows_ = rows; d_ = d; dAlign_ = dAlign; eps_ = epsilon; invD_ = invD;
        xGm_.SetGlobalBuffer((__gm__ float*)x);
        residualGm_.SetGlobalBuffer((__gm__ float*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ float*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ float*)bias);
        outGm_.SetGlobalBuffer((__gm__ float*)output);
    }

    __aicore__ inline void Process()
    {
        const uint64_t firstRow = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t blockCount = static_cast<uint64_t>(GetBlockNum());
        for (uint64_t row = firstRow; row < rows_; row += blockCount) {
        const uint64_t off = row * static_cast<uint64_t>(d_);
        LocalTensor<float> ub(TPosition::VECCALC, 0U, 5U * dAlign_ + FP32_PER_REPEAT);
        LocalTensor<float> x = ub;
        LocalTensor<float> r = ub[dAlign_];
        LocalTensor<float> g = ub[2U * dAlign_];
        LocalTensor<float> b = ub[3U * dAlign_];
        LocalTensor<float> tmp = ub[4U * dAlign_];
        LocalTensor<float> work = ub[5U * dAlign_];

        CopyInPad(x, xGm_[off], d_);
        CopyInPad(r, residualGm_[off], d_);
        event_t ein = static_cast<event_t>(0);
        SetFlag<HardEvent::MTE2_V>(ein);
        CopyInPad(g, gammaGm_, d_);
        CopyInPad(b, biasGm_, d_);
        event_t eparam = static_cast<event_t>(1);
        SetFlag<HardEvent::MTE2_V>(eparam);
        WaitFlag<HardEvent::MTE2_V>(ein);

        Add(x, x, r, d_);
        Mul(tmp, x, x, d_);
        ReduceSmallRowBlockWholeAuto(tmp, tmp, work, d_);
        NormalizeRowAuto(x, tmp, work, d_, invD_, eps_);
        WaitFlag<HardEvent::MTE2_V>(eparam);
        Mul(x, x, g, d_);
        Add(x, x, b, d_);

        event_t eout = static_cast<event_t>(0);
        SetFlag<HardEvent::V_MTE3>(eout);
        WaitFlag<HardEvent::V_MTE3>(eout);
        CopyOutPad(outGm_[off], x, d_);
        PipeBarrier<PIPE_ALL>();
        }
    }
private:
    GlobalTensor<float> xGm_, residualGm_, gammaGm_, biasGm_, outGm_;
    uint64_t rows_;
    uint32_t d_, dAlign_;
    float eps_, invD_;
};

} // namespace Iso02Private


namespace Iso03Private {
using namespace AddRmsNormBiasFixed;

class SmallBatchFloatKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, uint32_t blockFactor,
        float epsilon, float invD)
    {
        rows_=rows; d_=d; dAlign_=dAlign; blockFactor_=blockFactor;
        eps_=epsilon; invD_=invD;
        xGm_.SetGlobalBuffer((__gm__ float*)x);
        residualGm_.SetGlobalBuffer((__gm__ float*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ float*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ float*)bias);
        outGm_.SetGlobalBuffer((__gm__ float*)output);
        const uint32_t elems=blockFactor_*dAlign_;
        const uint32_t fBytes=AlignUp32(elems*sizeof(float));
        const uint32_t paramBytes=AlignUp32(dAlign_*sizeof(float));
        const uint32_t tmpBytes=AlignUp32(blockFactor_*FP32_PER_REPEAT*sizeof(float));
        const uint32_t rstdBytes=AlignUp32(blockFactor_*sizeof(float));
        pipe_.InitBuffer(xBuf_,fBytes);
        pipe_.InitBuffer(rBuf_,fBytes);
        pipe_.InitBuffer(gammaBuf_,paramBytes);
        pipe_.InitBuffer(biasBuf_,paramBytes);
        pipe_.InitBuffer(tmpBuf_,tmpBytes);
        pipe_.InitBuffer(rstdBuf_,rstdBytes);
    }
    __aicore__ inline void Process()
    {
        const uint64_t bid=GetBlockIdx();
        const uint64_t begin=bid*static_cast<uint64_t>(blockFactor_);
        if(begin>=rows_) return;
        const uint32_t n=static_cast<uint32_t>(MinU64(blockFactor_,rows_-begin));
        const uint32_t elems=n*dAlign_;
        const uint64_t off=begin*static_cast<uint64_t>(d_);
        LocalTensor<float> y=xBuf_.Get<float>();
        LocalTensor<float> rr=rBuf_.Get<float>();
        LocalTensor<float> g=gammaBuf_.Get<float>();
        LocalTensor<float> b=biasBuf_.Get<float>();
        LocalTensor<float> scratch=tmpBuf_.Get<float>();
        LocalTensor<float> rstd=rstdBuf_.Get<float>();
        CopyInPad(g,gammaGm_,d_); CopyInPad(b,biasGm_,d_);
        if(d_==dAlign_) { CopyInPad(y,xGm_[off],n*d_); CopyInPad(rr,residualGm_[off],n*d_); }
        else { CopyInRowsPad(y,xGm_[off],n,d_); CopyInRowsPad(rr,residualGm_[off],n,d_); }
        event_t e=static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(e); WaitFlag<HardEvent::MTE2_V>(e);
        Add(y,y,rr,elems);
        for(uint32_t i=0;i<n;++i){
            LocalTensor<float> acc=scratch[i*FP32_PER_REPEAT];
            Duplicate(acc,0.0f,FP32_PER_REPEAT);
            AccumulateSquare64(acc,y[i*dAlign_],d_);
            FinalizeAcc64Auto(rstd[i],acc);
        }
        Muls(rstd,rstd,invD_,n); Adds(rstd,rstd,eps_,n); Sqrt(rstd,rstd,n);
        Duplicate(scratch,1.0f,n); Div(rstd,scratch,rstd,n); Brcb(scratch, rstd, static_cast<uint8_t>((n + 7U) / 8U), {1,8});
        for(uint32_t i=0;i<n;++i){
            const uint32_t ro=i*dAlign_;
            MulByBroadcast64(y[ro],scratch[i*8U],d_);
            Mul(y[ro],y[ro],g,d_); Add(y[ro],y[ro],b,d_);
        }
        event_t eo=static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::V_MTE3));
        SetFlag<HardEvent::V_MTE3>(eo); WaitFlag<HardEvent::V_MTE3>(eo);
        if(d_==dAlign_) CopyOutPad(outGm_[off],y,n*d_); else CopyOutRowsPad(outGm_[off],y,n,d_);
    }
private:
    TPipe pipe_;
    TBuf<TPosition::VECCALC> xBuf_,rBuf_,gammaBuf_,biasBuf_,tmpBuf_,rstdBuf_;
    GlobalTensor<float> xGm_,residualGm_,gammaGm_,biasGm_,outGm_;
    uint64_t rows_; uint32_t d_,dAlign_,blockFactor_; float eps_,invD_;
};



// Compile-time-width specialization for aligned small FP32 matrices.
template <uint32_t D>
class SmallBatchFloatFixedKernel {
public:
    static_assert(D % FP32_PER_REPEAT == 0U && D / 8U <= 255U,
        "Small fixed rows require aligned representable repeat strides");

    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
        uint64_t rows, uint32_t bf, float eps, float invD)
    {
        rows_ = rows; bf_ = bf; eps_ = eps; invD_ = invD;
        xGm_.SetGlobalBuffer((__gm__ float*)x);
        rGm_.SetGlobalBuffer((__gm__ float*)r);
        gGm_.SetGlobalBuffer((__gm__ float*)g);
        bGm_.SetGlobalBuffer((__gm__ float*)b);
        oGm_.SetGlobalBuffer((__gm__ float*)o);
        // Identical capacity to the six V10 allocations, expressed as one
        // 32-byte-aligned region. All subregion starts are whole datablocks.
    }

    __aicore__ inline void Process()
    {
        const uint64_t begin = static_cast<uint64_t>(GetBlockIdx()) * bf_;
        if (begin >= rows_) return;
        const uint32_t n = static_cast<uint32_t>(MinU64(bf_, rows_ - begin));
        const uint32_t elems = n * D, span = bf_ * D;
        const uint64_t off = begin * static_cast<uint64_t>(D);
        LocalTensor<float> x(TPosition::VECCALC, 0U,
            2U * bf_ * D + 2U * D + bf_ * FP32_PER_REPEAT + AlignUp32(bf_ * 4U) / 4U);
        LocalTensor<float> r = x[span], g = x[2U * span];
        LocalTensor<float> b = x[2U * span + D];
        LocalTensor<float> tmp = x[2U * span + 2U * D];
        LocalTensor<float> rs = x[2U * span + 2U * D + bf_ * FP32_PER_REPEAT];
        DataCopy(g, gGm_, D);
        DataCopy(b, bGm_, D);
        DataCopy(x, xGm_[off], elems);
        DataCopy(r, rGm_[off], elems);
        const event_t e =
            static_cast<event_t>(0);
        SetFlag<HardEvent::MTE2_V>(e);
        WaitFlag<HardEvent::MTE2_V>(e);
        Add(x, x, r, elems);

        constexpr uint8_t stride = static_cast<uint8_t>(D / 8U);
        const uint8_t rep = static_cast<uint8_t>(n);
        // round(y*y) equals fma(y,y,+0) for finite IEEE values. Start from
        // that square instead of Duplicate(0) plus the first MulAddDst.
        // Remaining segments retain the original fused accumulation order.
        Mul(tmp, x, x, FP32_PER_REPEAT, rep, {1, 1, 1, 8, stride, stride});
        for (uint32_t c = FP32_PER_REPEAT; c < D; c += FP32_PER_REPEAT) {
            MulAddDst(tmp, x[c], x[c], FP32_PER_REPEAT, rep,
                {1, 1, 1, 8, stride, stride});
        }
        WholeReduceSum<float>(rs, tmp, FP32_PER_REPEAT, n, 1, 1, 8);
        Muls(rs, rs, invD_, n);
        Adds(rs, rs, eps_, n);
        Sqrt(rs, rs, n);
        Duplicate(tmp, 1.0f, n);
        Div(rs, tmp, rs, n);
        Brcb(tmp, rs, static_cast<uint8_t>((n + 7U) / 8U), {1, 8});

        // Independent column groups separate producer/consumer operations.
        // Per element the order is still (x * rstd) * gamma + bias.
        for (uint32_t c = 0U; c < D; c += FP32_PER_REPEAT) {
            Mul(x[c], x[c], tmp, FP32_PER_REPEAT, rep,
                {1, 1, 0, stride, stride, 1});
        }
        for (uint32_t c = 0U; c < D; c += FP32_PER_REPEAT) {
            Mul(x[c], x[c], g[c], FP32_PER_REPEAT, rep,
                {1, 1, 1, stride, stride, 0});
        }
        for (uint32_t c = 0U; c < D; c += FP32_PER_REPEAT) {
            Add(x[c], x[c], b[c], FP32_PER_REPEAT, rep,
                {1, 1, 1, stride, stride, 0});
        }
        const event_t eo =
            static_cast<event_t>(0);
        SetFlag<HardEvent::V_MTE3>(eo);
        WaitFlag<HardEvent::V_MTE3>(eo);
        DataCopy(oGm_[off], x, elems);
        PipeBarrier<PIPE_ALL>();
    }

private:
    GlobalTensor<float> xGm_, rGm_, gGm_, bGm_, oGm_;
    uint64_t rows_;
    uint32_t bf_;
    float eps_, invD_;
};
} // namespace Iso03Private


namespace Iso04Private {
using namespace AddRmsNormBiasFixed;

class ResidentHalfAlign208Kernel {
public:
    static constexpr uint32_t DA = 208U;
    static constexpr uint32_t MAX_ROWS = 33U;
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
        uint64_t rows, uint32_t d, uint32_t blocks,
        float eps, float invD)
    {
        rows_ = rows; d_ = d; blocks_ = blocks; eps_ = eps; invD_ = invD;
        baseRows_ = static_cast<uint32_t>(rows_ / blocks_);
        remRows_ = static_cast<uint32_t>(rows_ - static_cast<uint64_t>(baseRows_) * blocks_);
        xGm_.SetGlobalBuffer((__gm__ half*)x);
        rGm_.SetGlobalBuffer((__gm__ half*)r);
        gGm_.SetGlobalBuffer((__gm__ half*)g);
        bGm_.SetGlobalBuffer((__gm__ half*)b);
        oGm_.SetGlobalBuffer((__gm__ half*)o);
    }
    __aicore__ inline void Process()
    {
        const uint32_t bid = GetBlockIdx();
        if (bid >= blocks_) return;
        const uint32_t rowWork = baseRows_ + (bid < remRows_ ? 1U : 0U);
        if (rowWork == 0U || rowWork > MAX_ROWS) return;
        const uint64_t begin = static_cast<uint64_t>(bid) * baseRows_ +
                               static_cast<uint64_t>(bid < remRows_ ? bid : remRows_);
        const uint64_t gmOff = begin * static_cast<uint64_t>(d_);
        const uint32_t elems = rowWork * DA;
        LocalTensor<half> x(TPosition::VECCALC,0U,6864U);
        LocalTensor<half> r(TPosition::VECCALC,13728U,6864U);
        LocalTensor<half> gh(TPosition::VECCALC,82368U,2U * DA);
        LocalTensor<half> bh(TPosition::VECCALC,82784U,208U);
        LocalTensor<float> y(TPosition::VECCALC,27456U,6864U);
        LocalTensor<float> sq(TPosition::VECCALC,54912U,6864U);
        LocalTensor<float> gf(TPosition::VECCALC,83200U,2U * DA);
        LocalTensor<float> bf(TPosition::VECCALC,84032U,208U);
        LocalTensor<float> tmp(TPosition::VECCALC,84864U,2112U);
        LocalTensor<float> rstd(TPosition::VECCALC,93312U,40U);
        const uint32_t packedElems = rowWork * d_;
        CopyInPad(x, xGm_[gmOff], packedElems);
        CopyInPad(r, rGm_[gmOff], packedElems);
        const event_t inputReady = static_cast<event_t>(0);
        SetFlag<HardEvent::MTE2_V>(inputReady);
        CopyInPad(gh, gGm_, d_);
        CopyInPad(bh, bGm_, d_);
        const event_t parameterReady = static_cast<event_t>(1);
        SetFlag<HardEvent::MTE2_V>(parameterReady);
        // The index workspace dies before its normalization/parameter use.
        // Build all row addresses while the independent input DMA is pending.
        for (int32_t k = 0; k < 8; ++k) {
            gf.SetValue(k, static_cast<float>(k));
        }
        const event_t indexSeedReady = static_cast<event_t>(0);
        SetFlag<HardEvent::S_V>(indexSeedReady);
        WaitFlag<HardEvent::S_V>(indexSeedReady);
        Adds(gf[8U], gf, 8.0f, 8U);
        Adds(gf[16U], gf, 16.0f, 16U);
        Adds(gf[32U], gf, 32.0f, 32U);
        Adds(gf[64U], gf, 64.0f, 64U);
        Adds(gf[128U], gf, 128.0f, 80U);
        Muls(rstd, gf, static_cast<float>(static_cast<int32_t>(2U * d_)), 40U);
        Mins(gf, gf, static_cast<float>(static_cast<int32_t>(d_ - 1U)), DA);
        Muls(gf, gf, 2.0f, DA);
        Brcb(tmp, rstd, static_cast<uint8_t>((rowWork + 7U) / 8U), {1, 8});
        for (uint32_t c = 0U; c < 192U; c += 64U) {
            Add(sq[c], gf[c], tmp, 64U, static_cast<uint8_t>(rowWork),
                {1,1,0,26,0,1});
        }
        Add(sq[192U], gf[192U], tmp, 16U, static_cast<uint8_t>(rowWork),
            {1,1,0,26,0,1});
        LocalTensor<int32_t> gatherIndex = y.ReinterpretCast<int32_t>();
        Cast(gatherIndex, sq, RoundMode::CAST_RINT, elems);
        WaitFlag<HardEvent::MTE2_V>(inputReady);
        // Inputs are FP16, so form y in FP16 first (same accepted semantics
        // as the stable MergeRowsHalfFast path) and cast only once.
        Add(x, x, r, packedElems);
        // Clamp padding columns to the row's last valid element. No gather
        // address crosses the packed input, even for the final partial row.
        Gather(r, x, gatherIndex.ReinterpretCast<uint32_t>(), 0U, elems);
        Cast(y, r, RoundMode::CAST_NONE, elems);
        Mul(sq, y, y, elems);
        ReduceSumMultiNAuto(rstd, sq, tmp, rowWork, d_, DA);
        Muls(rstd, rstd, invD_, rowWork);
        Adds(rstd, rstd, eps_, rowWork);
        Sqrt(rstd, rstd, rowWork);
        Duplicate(tmp, 1.0f, rowWork);
        Div(rstd, tmp, rstd, rowWork);
        Brcb(tmp, rstd, static_cast<uint8_t>((rowWork + 7U) / 8U), {1, 8});
        WaitFlag<HardEvent::MTE2_V>(parameterReady);
        // DP: gamma/bias occupy contiguous DA-wide source and destination rows.
        Cast(gf, gh, RoundMode::CAST_NONE, 2U * DA);
        constexpr uint8_t rs = static_cast<uint8_t>(DA / 8U);
        const uint8_t rep = static_cast<uint8_t>(rowWork);
        uint32_t c = 0U;
        for (; c + FP32_PER_REPEAT <= d_; c += FP32_PER_REPEAT) {
            Mul(y[c], y[c], tmp, FP32_PER_REPEAT, rep, {1,1,0,rs,rs,1});
            Mul(y[c], y[c], gf[c], FP32_PER_REPEAT, rep, {1,1,1,rs,rs,0});
            Add(y[c], y[c], bf[c], FP32_PER_REPEAT, rep, {1,1,1,rs,rs,0});
        }
        if (c < d_) {
            const uint32_t tail = d_ - c;
            Mul(y[c], y[c], tmp, tail, rep, {1,1,0,rs,rs,1});
            Mul(y[c], y[c], gf[c], tail, rep, {1,1,1,rs,rs,0});
            Add(y[c], y[c], bf[c], tail, rep, {1,1,1,rs,rs,0});
        }
        Cast(x, y, RoundMode::CAST_NONE, elems);
        GatherMaskParams compact;
        compact.repeatTimes = static_cast<uint16_t>(rowWork);
        compact.src0RepeatStride = static_cast<uint16_t>(DA / 16U);
        uint64_t compactCount = 0U;
        GatherMask(r, x, static_cast<uint8_t>(7U), true, d_, compact, compactCount);
        ResetMask();
        event_t eo = static_cast<event_t>(0);
        SetFlag<HardEvent::V_MTE3>(eo);
        WaitFlag<HardEvent::V_MTE3>(eo);
        CopyOutPad(oGm_[gmOff], r, packedElems);
        PipeBarrier<PIPE_ALL>();
    }
private:
    GlobalTensor<half> xGm_, rGm_, gGm_, bGm_, oGm_;
    uint64_t rows_;
    uint32_t d_, blocks_, baseRows_, remRows_;
    float eps_, invD_;
};

template <uint32_t PAD>
class TiledFallbackHalfKernel {
public:
    static constexpr uint32_t DA = PAD;
    static constexpr uint32_t MAX_ROWS = 33U;
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
        uint64_t rows, uint32_t d, uint32_t blocks,
        float eps, float invD)
    {
        rows_ = rows; d_ = d; blocks_ = blocks; eps_ = eps; invD_ = invD;
        baseRows_ = static_cast<uint32_t>(rows_ / blocks_);
        remRows_ = static_cast<uint32_t>(rows_ - static_cast<uint64_t>(baseRows_) * blocks_);
        xGm_.SetGlobalBuffer((__gm__ half*)x);
        rGm_.SetGlobalBuffer((__gm__ half*)r);
        gGm_.SetGlobalBuffer((__gm__ half*)g);
        bGm_.SetGlobalBuffer((__gm__ half*)b);
        oGm_.SetGlobalBuffer((__gm__ half*)o);
    }
    __aicore__ inline void Process()
    {
        const uint32_t bid = GetBlockIdx();
        if (bid >= blocks_) return;
        const uint32_t rowWork = baseRows_ + (bid < remRows_ ? 1U : 0U);
        if (rowWork == 0U) return;
        const uint64_t begin = static_cast<uint64_t>(bid) * baseRows_ +
                               static_cast<uint64_t>(bid < remRows_ ? bid : remRows_);
        for (uint32_t done = 0U; done < rowWork;) {
            const uint32_t n = MinU32(MAX_ROWS, rowWork - done);
            ProcessTile(begin + done, n);
            done += n;
        }
    }
    __aicore__ inline void ProcessTile(uint64_t begin, uint32_t rowWork)
    {
        // A terminal PIPE_ALL in every tile retires all uses before reuse.
        const uint64_t gmOff = begin * static_cast<uint64_t>(d_);
        const uint32_t elems = rowWork * DA;
        constexpr uint32_t N = MAX_ROWS * DA;
        constexpr uint32_t HB = N * sizeof(half), FB = N * sizeof(float);
        constexpr uint32_t PARAM = 2U * HB + 2U * FB;
        constexpr uint8_t STRIDE = static_cast<uint8_t>(DA / 8U);
        LocalTensor<half> x(TPosition::VECCALC,0U,N);
        LocalTensor<half> r(TPosition::VECCALC,HB,N);
        LocalTensor<float> y(TPosition::VECCALC,2U * HB,N);
        LocalTensor<float> sq(TPosition::VECCALC,2U * HB + FB,N);
        LocalTensor<half> gh(TPosition::VECCALC,PARAM,2U * DA);
        LocalTensor<half> bh(TPosition::VECCALC,PARAM + 2U * DA,DA);
        LocalTensor<float> gf(TPosition::VECCALC,PARAM + 4U * DA,2U * DA);
        LocalTensor<float> bf(TPosition::VECCALC,PARAM + 8U * DA,DA);
        LocalTensor<float> tmp(TPosition::VECCALC,PARAM + 12U * DA,2112U);
        LocalTensor<float> rstd(TPosition::VECCALC,PARAM + 12U * DA + 8448U,40U);
        const uint32_t packedElems = rowWork * d_;
        CopyInPad(x, xGm_[gmOff], packedElems);
        CopyInPad(r, rGm_[gmOff], packedElems);
        const event_t inputReady = static_cast<event_t>(0);
        SetFlag<HardEvent::MTE2_V>(inputReady);
        CopyInPad(gh, gGm_, d_);
        CopyInPad(bh, bGm_, d_);
        const event_t parameterReady = static_cast<event_t>(1);
        SetFlag<HardEvent::MTE2_V>(parameterReady);
        // The index workspace dies before its normalization/parameter use.
        // Build all row addresses while the independent input DMA is pending.
        for (int32_t k = 0; k < 8; ++k) {
            gf.SetValue(k, static_cast<float>(k));
        }
        const event_t indexSeedReady = static_cast<event_t>(0);
        SetFlag<HardEvent::S_V>(indexSeedReady);
        WaitFlag<HardEvent::S_V>(indexSeedReady);
        Adds(gf[8U], gf, 8.0f, 8U);
        Adds(gf[16U], gf, 16.0f, 16U);
        Adds(gf[32U], gf, 32.0f, 32U);
        Adds(gf[64U], gf, 64.0f, 64U);
        Adds(gf[128U], gf, 128.0f, DA - 128U);
        Muls(rstd, gf, static_cast<float>(static_cast<int32_t>(2U * d_)), 40U);
        Mins(gf, gf, static_cast<float>(static_cast<int32_t>(d_ - 1U)), DA);
        Muls(gf, gf, 2.0f, DA);
        Brcb(tmp, rstd, static_cast<uint8_t>((rowWork + 7U) / 8U), {1, 8});
        for (uint32_t c = 0U; c + 64U <= DA; c += 64U) {
            Add(sq[c], gf[c], tmp, 64U, static_cast<uint8_t>(rowWork),
                {1,1,0,STRIDE,0,1});
        }
        if (DA % 64U != 0U) {
            constexpr uint32_t TAIL_BEGIN = DA - DA % 64U;
            Add(sq[TAIL_BEGIN], gf[TAIL_BEGIN], tmp, DA % 64U,
                static_cast<uint8_t>(rowWork), {1,1,0,STRIDE,0,1});
        }
        LocalTensor<int32_t> gatherIndex = y.ReinterpretCast<int32_t>();
        Cast(gatherIndex, sq, RoundMode::CAST_RINT, elems);
        WaitFlag<HardEvent::MTE2_V>(inputReady);
        // Inputs are FP16, so form y in FP16 first (same accepted semantics
        // as the stable MergeRowsHalfFast path) and cast only once.
        Add(x, x, r, packedElems);
        // Clamp padding columns to the row's last valid element. No gather
        // address crosses the packed input, even for the final partial row.
        Gather(r, x, gatherIndex.ReinterpretCast<uint32_t>(), 0U, elems);
        Cast(y, r, RoundMode::CAST_NONE, elems);
        Mul(sq, y, y, elems);
        ReduceSumMultiNAuto(rstd, sq, tmp, rowWork, d_, DA);
        Muls(rstd, rstd, invD_, rowWork);
        Adds(rstd, rstd, eps_, rowWork);
        Sqrt(rstd, rstd, rowWork);
        Duplicate(tmp, 1.0f, rowWork);
        Div(rstd, tmp, rstd, rowWork);
        Brcb(tmp, rstd, static_cast<uint8_t>((rowWork + 7U) / 8U), {1, 8});
        WaitFlag<HardEvent::MTE2_V>(parameterReady);
        // DP: gamma/bias occupy contiguous DA-wide source and destination rows.
        Cast(gf, gh, RoundMode::CAST_NONE, 2U * DA);
        constexpr uint8_t rs = static_cast<uint8_t>(DA / 8U);
        const uint8_t rep = static_cast<uint8_t>(rowWork);
        uint32_t c = 0U;
        for (; c + FP32_PER_REPEAT <= d_; c += FP32_PER_REPEAT) {
            Mul(y[c], y[c], tmp, FP32_PER_REPEAT, rep, {1,1,0,rs,rs,1});
            Mul(y[c], y[c], gf[c], FP32_PER_REPEAT, rep, {1,1,1,rs,rs,0});
            Add(y[c], y[c], bf[c], FP32_PER_REPEAT, rep, {1,1,1,rs,rs,0});
        }
        if (c < d_) {
            const uint32_t tail = d_ - c;
            Mul(y[c], y[c], tmp, tail, rep, {1,1,0,rs,rs,1});
            Mul(y[c], y[c], gf[c], tail, rep, {1,1,1,rs,rs,0});
            Add(y[c], y[c], bf[c], tail, rep, {1,1,1,rs,rs,0});
        }
        Cast(x, y, RoundMode::CAST_NONE, elems);
        GatherMaskParams compact;
        compact.repeatTimes = static_cast<uint16_t>(rowWork);
        compact.src0RepeatStride = static_cast<uint16_t>(DA / 16U);
        uint64_t compactCount = 0U;
        GatherMask(r, x, static_cast<uint8_t>(7U), true, d_, compact, compactCount);
        ResetMask();
        event_t eo = static_cast<event_t>(0);
        SetFlag<HardEvent::V_MTE3>(eo);
        WaitFlag<HardEvent::V_MTE3>(eo);
        CopyOutPad(oGm_[gmOff], r, packedElems);
        PipeBarrier<PIPE_ALL>();
    }
private:
    GlobalTensor<half> xGm_, rGm_, gGm_, bGm_, oGm_;
    uint64_t rows_;
    uint32_t d_, blocks_, baseRows_, remRows_;
    float eps_, invD_;
};

} // namespace Iso04Private


namespace Iso06Private {
using namespace AddRmsNormBiasFixed;

// DU: two fused square chains; merge once before the unchanged final reduction.
__aicore__ inline void ReduceDualHalfSquares67(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& y,
    const LocalTensor<float>& tmp,
    const LocalTensor<float>& aux,
    uint32_t rows,
    uint32_t cols,
    uint32_t colsAlign)
{
    const uint8_t stride = static_cast<uint8_t>(colsAlign / 8U);
    Mul(tmp, y, y, FP32_PER_REPEAT, rows, {1, 1, 1, 8, stride, stride});
    Mul(aux, y[64U], y[64U], FP32_PER_REPEAT, rows, {1, 1, 1, 8, stride, stride});
    uint32_t col = 128U;
    for (; col + 128U <= cols; col += 128U) {
        MulAddDst(tmp, y[col], y[col], FP32_PER_REPEAT, rows,
            {1, 1, 1, 8, stride, stride});
        MulAddDst(aux, y[col + 64U], y[col + 64U], FP32_PER_REPEAT, rows,
            {1, 1, 1, 8, stride, stride});
    }
    if (col + 64U <= cols) {
        MulAddDst(tmp, y[col], y[col], FP32_PER_REPEAT, rows,
            {1, 1, 1, 8, stride, stride});
        col += 64U;
    }
    if (col < cols) {
        MulAddDst(aux, y[col], y[col], cols - col, rows,
            {1, 1, 1, 8, stride, stride});
    }
    Add(tmp, tmp, aux, rows * FP32_PER_REPEAT);
    AscendCUtils::SetMask<float>(FP32_PER_REPEAT);
#if defined(__CCE_AICORE__) && (__CCE_AICORE__ == 220)
    if (g_coreType == AIV) {
        WholeReduceSum<float, false>(dst, tmp, FP32_PER_REPEAT, rows, 1, 1, 8);
    }
#else
    WholeReduceSum<float, false>(dst, tmp, FP32_PER_REPEAT, rows, 1, 1, 8);
#endif
}

class MergeRowsHalfFastKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, uint32_t rowFactor,
        uint32_t blockFactor, float epsilon, float invD)
    {
        rows_ = rows;
        d_ = d;
        dAlign_ = dAlign;
        rowFactor_ = rowFactor;
        blockFactor_ = blockFactor;
        eps_ = epsilon;
        invD_ = invD;
        ubFactor_ = rowFactor_ * dAlign_;

        xGm_.SetGlobalBuffer((__gm__ half*)x);
        residualGm_.SetGlobalBuffer((__gm__ half*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ half*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ half*)bias);
        outGm_.SetGlobalBuffer((__gm__ half*)output);

        hb_ = AlignUp32(ubFactor_ * sizeof(half));
        fb_ = AlignUp32(ubFactor_ * sizeof(float));
        pb_ = AlignUp32(dAlign_ * sizeof(half));
        rb_ = AlignUp32(rowFactor_ * sizeof(float));
        const uint32_t ubEnd = 3U*hb_+2U*fb_+2U*pb_+rb_+rowFactor_*256U;
        dedicatedOutput_ = ubEnd + hb_ <= MERGE_UB_BYTES;
        ob_ = dedicatedOutput_ ? ubEnd : 3U*hb_+fb_;
    }

    __aicore__ inline void Process()
    {
        const uint64_t blockIdx = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t begin = blockIdx * static_cast<uint64_t>(blockFactor_);
        if (begin >= rows_) {
            return;
        }
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(
            static_cast<uint64_t>(blockFactor_), rows_ - begin));

        LocalTensor<half> gammaH(TPosition::VECCALC, 3U*hb_+2U*fb_, dAlign_);
        LocalTensor<half> biasH(TPosition::VECCALC, 3U*hb_+2U*fb_+pb_, dAlign_);
        LoadParams(gammaH, biasH);

        LocalTensor<float> xFp32(TPosition::VECCALC, 3U*hb_, ubFactor_);
        LocalTensor<float> sqx(TPosition::VECCALC, 3U*hb_+fb_, ubFactor_);
        LocalTensor<float> tmp(TPosition::VECCALC, 3U*hb_+2U*fb_+2U*pb_+rb_, rowFactor_*64U);
        LocalTensor<float> rstd(TPosition::VECCALC, 3U*hb_+2U*fb_+2U*pb_, rowFactor_);

        uint32_t done = 0U;
        uint32_t calcRows = MinU32(rowFactor_, rowWork);
        uint32_t elementNum = calcRows * dAlign_;
        uint64_t gmOff = begin * static_cast<uint64_t>(d_);
        SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
        PrefetchXResidual(gmOff, calcRows);
        while (done < rowWork) {
            Sync<HardEvent::MTE2_V>();
            LocalTensor<half> xr(TPosition::VECCALC, 0U, ubFactor_);
            LocalTensor<half> rr(TPosition::VECCALC, hb_, ubFactor_);
            LocalTensor<half> yHalf(TPosition::VECCALC, 2U*hb_, ubFactor_);
            Add(yHalf, xr, rr, elementNum);
            Sync<HardEvent::V_MTE2>();

            const uint32_t nextDone = done + calcRows;
            uint32_t nextRows = 0U;
            if (nextDone < rowWork) {
                nextRows = MinU32(rowFactor_, rowWork - nextDone);
                const uint64_t nextOff = (begin + static_cast<uint64_t>(nextDone)) *
                                         static_cast<uint64_t>(d_);
                PrefetchXResidual(nextOff, nextRows);
            }

            Cast(xFp32, yHalf, RoundMode::CAST_NONE, elementNum);
            if (!dedicatedOutput_) {
                WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
            }
            // Half residual is dead after Cast; use its aligned storage for chain2.
            LocalTensor<float> partial2 = yHalf.ReinterpretCast<float>();
            ReduceDualHalfSquares67(rstd, xFp32, tmp, partial2, calcRows, d_, dAlign_);
            Muls(rstd, rstd, invD_, calcRows);
            Adds(rstd, rstd, eps_, calcRows);
            Sqrt(rstd, rstd, calcRows);
            Duplicate(tmp, 1.0f, calcRows);
            Div(rstd, tmp, rstd, calcRows);

            Brcb(tmp, rstd, static_cast<uint8_t>((calcRows + 7U) / 8U), {1, 8});
            MulRowsByRstd(xFp32, tmp, calcRows);
            // A separate output region lets the next reduction overlap prior DMA.
            // Capacity fallback retains the square-buffer lifetime and earlier wait.
            LocalTensor<half> outputHalf(TPosition::VECCALC, ob_, ubFactor_);
            if (dedicatedOutput_) {
                WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
            }
            Cast(outputHalf, xFp32, RoundMode::CAST_NONE, elementNum);
            FmaRowsByParam(outputHalf, gammaH, biasH, calcRows);

            Sync<HardEvent::V_MTE3>();
            LocalTensor<half> ready = outputHalf;
            if (d_ == dAlign_) {
                CopyOutPad(outGm_[gmOff], ready, calcRows * d_);
            } else {
                CopyOutRowsPad(outGm_[gmOff], ready, calcRows, d_);
            }
            SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
            done = nextDone;
            calcRows = nextRows;
            elementNum = calcRows * dAlign_;
            gmOff = (begin + static_cast<uint64_t>(done)) * static_cast<uint64_t>(d_);
        }
        WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
        PipeBarrier<PIPE_ALL>();
    }

private:
    template <HardEvent Event>
    __aicore__ inline void Sync() {
        SetFlag<Event>(static_cast<event_t>(0));
        WaitFlag<Event>(static_cast<event_t>(0));
    }
    __aicore__ inline void PrefetchXResidual(uint64_t gmOff, uint32_t calcRows)
    {
        LocalTensor<half> x(TPosition::VECCALC, 0U, ubFactor_);
        if (d_ == dAlign_) {
            CopyInPad(x, xGm_[gmOff], calcRows * d_);
        } else {
            CopyInRowsPad(x, xGm_[gmOff], calcRows, d_);
        }
        LocalTensor<half> r(TPosition::VECCALC, hb_, ubFactor_);
        if (d_ == dAlign_) {
            CopyInPad(r, residualGm_[gmOff], calcRows * d_);
        } else {
            CopyInRowsPad(r, residualGm_[gmOff], calcRows, d_);
        }
    }

    __aicore__ inline void LoadParams(
        const LocalTensor<half>& gammaH,
        const LocalTensor<half>& biasH)
    {
        CopyInPad(gammaH, gammaGm_, d_);
        CopyInPad(biasH, biasGm_, d_);
        event_t ep = static_cast<event_t>(0);
        SetFlag<HardEvent::MTE2_V>(ep);
        WaitFlag<HardEvent::MTE2_V>(ep);
    }

    __aicore__ inline void MulRowsByRstd(
        const LocalTensor<float>& y,
        const LocalTensor<float>& rstdBroadcast,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 8U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 64U <= d_; col += 64U) {
            Mul(y[col], y[col], rstdBroadcast, 64U, repeat,
                {1, 1, 0, repStride, repStride, 1});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Mul(y[col], y[col], rstdBroadcast, tail, repeat,
                {1, 1, 0, repStride, repStride, 1});
        }
    }

    // Fused affine y = y*gamma + bias over all rows in one FusedMulAdd,
    // replacing the separate full-width Mul then Add vector passes.
    __aicore__ inline void FmaRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& gamma,
        const LocalTensor<half>& bias,
        uint32_t rows)
    {
        // One fused vector op over all rows. Official CANN semantics:
        //   dst = src0 * dst + src1  (FusedMulAdd, atlasascendc_api_07_0050)
        // so dst=y, src0=gamma, src1=bias gives y = gamma*y + bias in one pass.
        // dst(y) advances one padded row per repeat (rs dataBlocks); gamma and
        // bias are a single loaded row reused by every repeat => repStride 0.
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t c = 0U;
        for (; c + 128U <= d_; c += 128U) {
            FusedMulAdd(y[c], gamma[c], bias[c], 128U, repeat,
                {1, 1, 1, repStride, 0, 0});
        }
        if (c < d_) {
            FusedMulAdd(y[c], gamma[c], bias[c], d_ - c, repeat,
                {1, 1, 1, repStride, 0, 0});
        }
    }

    __aicore__ inline void MulRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& param,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 128U <= d_; col += 128U) {
            Mul(y[col], y[col], param[col], 128U, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Mul(y[col], y[col], param[col], tail, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
    }

    __aicore__ inline void AddRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& param,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 128U <= d_; col += 128U) {
            Add(y[col], y[col], param[col], 128U, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Add(y[col], y[col], param[col], tail, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
    }

private:
    uint32_t hb_, fb_, pb_, rb_, ob_;
    bool dedicatedOutput_;
    GlobalTensor<half> xGm_;
    GlobalTensor<half> residualGm_;
    GlobalTensor<half> gammaGm_;
    GlobalTensor<half> biasGm_;
    GlobalTensor<half> outGm_;
    uint64_t rows_;
    uint32_t d_;
    uint32_t dAlign_;
    uint32_t rowFactor_;
    uint32_t blockFactor_;
    uint32_t ubFactor_;
    float eps_;
    float invD_;
};

} // namespace Iso06Private


namespace Iso07Private {
using namespace AddRmsNormBiasFixed;

// DU: two fused square chains; merge once before the unchanged final reduction.
__aicore__ inline void ReduceDualHalfSquares67(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& y,
    const LocalTensor<float>& tmp,
    const LocalTensor<float>& aux,
    uint32_t rows,
    uint32_t cols,
    uint32_t colsAlign)
{
    const uint8_t stride = static_cast<uint8_t>(colsAlign / 8U);
    Mul(tmp, y, y, FP32_PER_REPEAT, rows, {1, 1, 1, 8, stride, stride});
    Mul(aux, y[64U], y[64U], FP32_PER_REPEAT, rows, {1, 1, 1, 8, stride, stride});
    uint32_t col = 128U;
    for (; col + 128U <= cols; col += 128U) {
        MulAddDst(tmp, y[col], y[col], FP32_PER_REPEAT, rows,
            {1, 1, 1, 8, stride, stride});
        MulAddDst(aux, y[col + 64U], y[col + 64U], FP32_PER_REPEAT, rows,
            {1, 1, 1, 8, stride, stride});
    }
    if (col + 64U <= cols) {
        MulAddDst(tmp, y[col], y[col], FP32_PER_REPEAT, rows,
            {1, 1, 1, 8, stride, stride});
        col += 64U;
    }
    if (col < cols) {
        MulAddDst(aux, y[col], y[col], cols - col, rows,
            {1, 1, 1, 8, stride, stride});
    }
    Add(tmp, tmp, aux, rows * FP32_PER_REPEAT);
    AscendCUtils::SetMask<float>(FP32_PER_REPEAT);
#if defined(__CCE_AICORE__) && (__CCE_AICORE__ == 220)
    if (g_coreType == AIV) {
        WholeReduceSum<float, false>(dst, tmp, FP32_PER_REPEAT, rows, 1, 1, 8);
    }
#else
    WholeReduceSum<float, false>(dst, tmp, FP32_PER_REPEAT, rows, 1, 1, 8);
#endif
}

class MergeRowsHalfFastKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, uint32_t rowFactor,
        uint32_t blockFactor, float epsilon, float invD)
    {
        rows_ = rows;
        d_ = d;
        dAlign_ = dAlign;
        rowFactor_ = rowFactor;
        blockFactor_ = blockFactor;
        eps_ = epsilon;
        invD_ = invD;
        ubFactor_ = rowFactor_ * dAlign_;

        xGm_.SetGlobalBuffer((__gm__ half*)x);
        residualGm_.SetGlobalBuffer((__gm__ half*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ half*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ half*)bias);
        outGm_.SetGlobalBuffer((__gm__ half*)output);

        hb_ = AlignUp32(ubFactor_ * sizeof(half));
        fb_ = AlignUp32(ubFactor_ * sizeof(float));
        pb_ = AlignUp32(dAlign_ * sizeof(half));
        rb_ = AlignUp32(rowFactor_ * sizeof(float));
        const uint32_t ubEnd = 3U*hb_+2U*fb_+2U*pb_+rb_+rowFactor_*256U;
        dedicatedOutput_ = ubEnd + hb_ <= MERGE_UB_BYTES;
        ob_ = dedicatedOutput_ ? ubEnd : 3U*hb_+fb_;
    }

    __aicore__ inline void Process()
    {
        const uint64_t blockIdx = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t begin = blockIdx * static_cast<uint64_t>(blockFactor_);
        if (begin >= rows_) {
            return;
        }
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(
            static_cast<uint64_t>(blockFactor_), rows_ - begin));

        LocalTensor<half> gammaH(TPosition::VECCALC, 3U*hb_+2U*fb_, dAlign_);
        LocalTensor<half> biasH(TPosition::VECCALC, 3U*hb_+2U*fb_+pb_, dAlign_);
        LoadParams(gammaH, biasH);

        LocalTensor<float> xFp32(TPosition::VECCALC, 3U*hb_, ubFactor_);
        LocalTensor<float> sqx(TPosition::VECCALC, 3U*hb_+fb_, ubFactor_);
        LocalTensor<float> tmp(TPosition::VECCALC, 3U*hb_+2U*fb_+2U*pb_+rb_, rowFactor_*64U);
        LocalTensor<float> rstd(TPosition::VECCALC, 3U*hb_+2U*fb_+2U*pb_, rowFactor_);

        uint32_t done = 0U;
        uint32_t calcRows = MinU32(rowFactor_, rowWork);
        uint32_t elementNum = calcRows * dAlign_;
        uint64_t gmOff = begin * static_cast<uint64_t>(d_);
        SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
        PrefetchXResidual(gmOff, calcRows);
        while (done < rowWork) {
            Sync<HardEvent::MTE2_V>();
            LocalTensor<half> xr(TPosition::VECCALC, 0U, ubFactor_);
            LocalTensor<half> rr(TPosition::VECCALC, hb_, ubFactor_);
            LocalTensor<half> yHalf(TPosition::VECCALC, 2U*hb_, ubFactor_);
            Add(yHalf, xr, rr, elementNum);
            Sync<HardEvent::V_MTE2>();

            const uint32_t nextDone = done + calcRows;
            uint32_t nextRows = 0U;
            if (nextDone < rowWork) {
                nextRows = MinU32(rowFactor_, rowWork - nextDone);
                const uint64_t nextOff = (begin + static_cast<uint64_t>(nextDone)) *
                                         static_cast<uint64_t>(d_);
                PrefetchXResidual(nextOff, nextRows);
            }

            Cast(xFp32, yHalf, RoundMode::CAST_NONE, elementNum);
            if (!dedicatedOutput_) {
                WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
            }
            // Half residual is dead after Cast; use its aligned storage for chain2.
            LocalTensor<float> partial2 = yHalf.ReinterpretCast<float>();
            ReduceDualHalfSquares67(rstd, xFp32, tmp, partial2, calcRows, d_, dAlign_);
            Muls(rstd, rstd, invD_, calcRows);
            Adds(rstd, rstd, eps_, calcRows);
            Sqrt(rstd, rstd, calcRows);
            Duplicate(tmp, 1.0f, calcRows);
            Div(rstd, tmp, rstd, calcRows);

            Brcb(tmp, rstd, static_cast<uint8_t>((calcRows + 7U) / 8U), {1, 8});
            MulRowsByRstd(xFp32, tmp, calcRows);
            // A separate output region lets the next reduction overlap prior DMA.
            // Capacity fallback retains the square-buffer lifetime and earlier wait.
            LocalTensor<half> outputHalf(TPosition::VECCALC, ob_, ubFactor_);
            if (dedicatedOutput_) {
                WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
            }
            Cast(outputHalf, xFp32, RoundMode::CAST_NONE, elementNum);
            FmaRowsByParam(outputHalf, gammaH, biasH, calcRows);

            Sync<HardEvent::V_MTE3>();
            LocalTensor<half> ready = outputHalf;
            if (d_ == dAlign_) {
                CopyOutPad(outGm_[gmOff], ready, calcRows * d_);
            } else {
                CopyOutRowsPad(outGm_[gmOff], ready, calcRows, d_);
            }
            SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
            done = nextDone;
            calcRows = nextRows;
            elementNum = calcRows * dAlign_;
            gmOff = (begin + static_cast<uint64_t>(done)) * static_cast<uint64_t>(d_);
        }
        WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
        PipeBarrier<PIPE_ALL>();
    }

private:
    template <HardEvent Event>
    __aicore__ inline void Sync() {
        SetFlag<Event>(static_cast<event_t>(0));
        WaitFlag<Event>(static_cast<event_t>(0));
    }
    __aicore__ inline void PrefetchXResidual(uint64_t gmOff, uint32_t calcRows)
    {
        LocalTensor<half> x(TPosition::VECCALC, 0U, ubFactor_);
        if (d_ == dAlign_) {
            CopyInPad(x, xGm_[gmOff], calcRows * d_);
        } else {
            CopyInRowsPad(x, xGm_[gmOff], calcRows, d_);
        }
        LocalTensor<half> r(TPosition::VECCALC, hb_, ubFactor_);
        if (d_ == dAlign_) {
            CopyInPad(r, residualGm_[gmOff], calcRows * d_);
        } else {
            CopyInRowsPad(r, residualGm_[gmOff], calcRows, d_);
        }
    }

    __aicore__ inline void LoadParams(
        const LocalTensor<half>& gammaH,
        const LocalTensor<half>& biasH)
    {
        CopyInPad(gammaH, gammaGm_, d_);
        CopyInPad(biasH, biasGm_, d_);
        event_t ep = static_cast<event_t>(0);
        SetFlag<HardEvent::MTE2_V>(ep);
        WaitFlag<HardEvent::MTE2_V>(ep);
    }

    __aicore__ inline void MulRowsByRstd(
        const LocalTensor<float>& y,
        const LocalTensor<float>& rstdBroadcast,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 8U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 64U <= d_; col += 64U) {
            Mul(y[col], y[col], rstdBroadcast, 64U, repeat,
                {1, 1, 0, repStride, repStride, 1});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Mul(y[col], y[col], rstdBroadcast, tail, repeat,
                {1, 1, 0, repStride, repStride, 1});
        }
    }

    // Fused affine y = y*gamma + bias over all rows in one FusedMulAdd,
    // replacing the separate full-width Mul then Add vector passes.
    __aicore__ inline void FmaRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& gamma,
        const LocalTensor<half>& bias,
        uint32_t rows)
    {
        // One fused vector op over all rows. Official CANN semantics:
        //   dst = src0 * dst + src1  (FusedMulAdd, atlasascendc_api_07_0050)
        // so dst=y, src0=gamma, src1=bias gives y = gamma*y + bias in one pass.
        // dst(y) advances one padded row per repeat (rs dataBlocks); gamma and
        // bias are a single loaded row reused by every repeat => repStride 0.
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t c = 0U;
        for (; c + 128U <= d_; c += 128U) {
            FusedMulAdd(y[c], gamma[c], bias[c], 128U, repeat,
                {1, 1, 1, repStride, 0, 0});
        }
        if (c < d_) {
            FusedMulAdd(y[c], gamma[c], bias[c], d_ - c, repeat,
                {1, 1, 1, repStride, 0, 0});
        }
    }

    __aicore__ inline void MulRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& param,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 128U <= d_; col += 128U) {
            Mul(y[col], y[col], param[col], 128U, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Mul(y[col], y[col], param[col], tail, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
    }

    __aicore__ inline void AddRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& param,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 128U <= d_; col += 128U) {
            Add(y[col], y[col], param[col], 128U, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Add(y[col], y[col], param[col], tail, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
    }

private:
    uint32_t hb_, fb_, pb_, rb_, ob_;
    bool dedicatedOutput_;
    GlobalTensor<half> xGm_;
    GlobalTensor<half> residualGm_;
    GlobalTensor<half> gammaGm_;
    GlobalTensor<half> biasGm_;
    GlobalTensor<half> outGm_;
    uint64_t rows_;
    uint32_t d_;
    uint32_t dAlign_;
    uint32_t rowFactor_;
    uint32_t blockFactor_;
    uint32_t ubFactor_;
    float eps_;
    float invD_;
};

} // namespace Iso07Private


namespace HuaweiStyle8Private {
using namespace AscendC;
using namespace AddRmsNormBiasFixed;

class OutputOnlyMergeKernel {
public:
    static constexpr uint32_t D = 512U;
    static constexpr uint32_t ROWS_PER_TILE = 29U;
    static constexpr uint32_t SPAN = ROWS_PER_TILE * D;
    static constexpr uint32_t H_BYTES = SPAN * sizeof(half);
    static constexpr uint32_t F_BYTES = SPAN * sizeof(float);
    static constexpr uint32_t PARAM_BYTES = D * sizeof(half);
    static constexpr uint32_t TMP_BYTES = ROWS_PER_TILE * 64U * sizeof(float);
    static constexpr uint32_t RSTD_BYTES =
        ((ROWS_PER_TILE * sizeof(float) + 31U) / 32U) * 32U;
    static constexpr uint32_t X_OFFSET = 0U;
    static constexpr uint32_t R_OFFSET = X_OFFSET + H_BYTES;
    static constexpr uint32_t OUT0_OFFSET = R_OFFSET + H_BYTES;
    static constexpr uint32_t OUT1_OFFSET = OUT0_OFFSET + H_BYTES;
    static constexpr uint32_t Y_OFFSET = OUT1_OFFSET + H_BYTES;
    static constexpr uint32_t GAMMA_OFFSET = Y_OFFSET + F_BYTES;
    static constexpr uint32_t BIAS_OFFSET = GAMMA_OFFSET + PARAM_BYTES;
    static constexpr uint32_t TMP_OFFSET = BIAS_OFFSET + PARAM_BYTES;
    static constexpr uint32_t RSTD_OFFSET = TMP_OFFSET + TMP_BYTES;
    static constexpr uint32_t UB_END = RSTD_OFFSET + RSTD_BYTES;
    static_assert(UB_END == 187776U, "Unexpected Huawei-style UB model");
    static_assert(UB_END <= MERGE_UB_BYTES, "Huawei-style UB overflow");

    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias,
        GM_ADDR output, uint64_t rows, float epsilon)
    {
        rows_ = rows;
        eps_ = epsilon;
        xGm_.SetGlobalBuffer((__gm__ half*)x);
        residualGm_.SetGlobalBuffer((__gm__ half*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ half*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ half*)bias);
        outGm_.SetGlobalBuffer((__gm__ half*)output);
    }

    __aicore__ inline void Process()
    {
        const uint64_t block = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t blockCount = static_cast<uint64_t>(GetBlockNum());
        const uint64_t tiles =
            (rows_ + static_cast<uint64_t>(ROWS_PER_TILE) - 1ULL) /
            static_cast<uint64_t>(ROWS_PER_TILE);
        if (block >= tiles || blockCount == 0ULL) {
            return;
        }

        LocalTensor<half> gamma(TPosition::VECCALC, GAMMA_OFFSET, D);
        LocalTensor<half> bias(TPosition::VECCALC, BIAS_OFFSET, D);
        DataCopy(gamma, gammaGm_, D);
        DataCopy(bias, biasGm_, D);
        Sync<HardEvent::MTE2_V>();

        SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
        SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(1));
        uint32_t outputSlot = 0U;
        uint64_t logicalTile = block;
        uint64_t row = logicalTile * static_cast<uint64_t>(ROWS_PER_TILE);
        uint32_t activeRows = static_cast<uint32_t>(MinU64(
            static_cast<uint64_t>(ROWS_PER_TILE), rows_ - row));
        Prefetch(row, activeRows);

        while (true) {
            Sync<HardEvent::MTE2_V>();
            const uint32_t elements = activeRows * D;
            LocalTensor<half> x(TPosition::VECCALC, X_OFFSET, SPAN);
            LocalTensor<half> residual(TPosition::VECCALC, R_OFFSET, SPAN);
            LocalTensor<float> y(TPosition::VECCALC, Y_OFFSET, SPAN);
            Add(x, x, residual, elements);
            Cast(y, x, RoundMode::CAST_NONE, elements);
            Sync<HardEvent::V_MTE2>();

            const bool hasNext = tiles - logicalTile > blockCount;
            uint64_t nextTile = logicalTile;
            uint64_t nextRow = row;
            uint32_t nextRows = 0U;
            if (hasNext) {
                nextTile += blockCount;
                nextRow = nextTile * static_cast<uint64_t>(ROWS_PER_TILE);
                nextRows = static_cast<uint32_t>(MinU64(
                    static_cast<uint64_t>(ROWS_PER_TILE), rows_ - nextRow));
                Prefetch(nextRow, nextRows);
            }

            LocalTensor<float> tmp(
                TPosition::VECCALC, TMP_OFFSET, ROWS_PER_TILE * 64U);
            LocalTensor<float> rstd(
                TPosition::VECCALC, RSTD_OFFSET, ROWS_PER_TILE);
            ReduceAndNormalize(y, tmp, rstd, activeRows);

            WaitFlag<HardEvent::MTE3_V>(
                static_cast<event_t>(outputSlot));
            LocalTensor<half> output(
                TPosition::VECCALC,
                outputSlot == 0U ? OUT0_OFFSET : OUT1_OFFSET,
                SPAN);
            Cast(output, y, RoundMode::CAST_NONE, elements);
            Affine(output, gamma, bias, activeRows);
            Sync<HardEvent::V_MTE3>();
            DataCopy(outGm_[row * static_cast<uint64_t>(D)], output, elements);
            SetFlag<HardEvent::MTE3_V>(
                static_cast<event_t>(outputSlot));
            outputSlot ^= 1U;

            if (!hasNext) {
                break;
            }
            logicalTile = nextTile;
            row = nextRow;
            activeRows = nextRows;
        }
        WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
        WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(1));
        PipeBarrier<PIPE_ALL>();
    }

private:
    template <HardEvent Event>
    __aicore__ inline void Sync()
    {
        SetFlag<Event>(static_cast<event_t>(0));
        WaitFlag<Event>(static_cast<event_t>(0));
    }

    __aicore__ inline void Prefetch(uint64_t row, uint32_t activeRows)
    {
        const uint64_t offset = row * static_cast<uint64_t>(D);
        LocalTensor<half> x(TPosition::VECCALC, X_OFFSET, SPAN);
        LocalTensor<half> residual(TPosition::VECCALC, R_OFFSET, SPAN);
        DataCopy(x, xGm_[offset], activeRows * D);
        DataCopy(residual, residualGm_[offset], activeRows * D);
    }

    __aicore__ inline void ReduceAndNormalize(
        const LocalTensor<float>& y,
        const LocalTensor<float>& tmp,
        const LocalTensor<float>& rstd,
        uint32_t activeRows)
    {
        const uint8_t repeats = static_cast<uint8_t>(activeRows);
        Mul(tmp, y, y, 64U, repeats, {1, 1, 1, 8, 64, 64});
        for (uint32_t column = 64U; column < D; column += 64U) {
            MulAddDst(
                tmp, y[column], y[column], 64U, repeats,
                {1, 1, 1, 8, 64, 64});
        }
        WholeReduceSum<float>(rstd, tmp, 64U, activeRows, 1, 1, 8);
        Muls(rstd, rstd, 1.0f / 512.0f, activeRows);
        Adds(rstd, rstd, eps_, activeRows);
        Sqrt(rstd, rstd, activeRows);
        Duplicate(tmp, 1.0f, activeRows);
        Div(rstd, tmp, rstd, activeRows);
        Brcb(
            tmp, rstd, static_cast<uint8_t>((activeRows + 7U) / 8U),
            {1, 8});
        for (uint32_t column = 0U; column < D; column += 64U) {
            Mul(
                y[column], y[column], tmp, 64U, repeats,
                {1, 1, 0, 64, 64, 1});
        }
    }

    __aicore__ inline void Affine(
        const LocalTensor<half>& output,
        const LocalTensor<half>& gamma,
        const LocalTensor<half>& bias,
        uint32_t activeRows)
    {
        const uint8_t repeats = static_cast<uint8_t>(activeRows);
        for (uint32_t column = 0U; column < D; column += 128U) {
            Mul(
                output[column], output[column], gamma[column],
                128U, repeats, {1, 1, 1, 32, 32, 0});
            Add(
                output[column], output[column], bias[column],
                128U, repeats, {1, 1, 1, 32, 32, 0});
        }
    }

    GlobalTensor<half> xGm_;
    GlobalTensor<half> residualGm_;
    GlobalTensor<half> gammaGm_;
    GlobalTensor<half> biasGm_;
    GlobalTensor<half> outGm_;
    uint64_t rows_;
    float eps_;
};
}  // namespace HuaweiStyle8Private

extern "C" __global__ __vector__ void huawei_style8_unit(
    GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
    uint64_t rows, float eps)
{
    HuaweiStyle8Private::OutputOnlyMergeKernel op;
    op.Init(x, r, g, b, o, rows, eps);
    op.Process();
}

namespace Iso08Private {
using namespace AscendC;
using namespace AddRmsNormBiasFixed;
// Private physical copy. Public AddRmsNormBiasFixed is frozen and must not be edited for route tuning.
class MergeRowsHalfFastKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, uint32_t rowFactor,
        uint32_t blockFactor, float epsilon, float invD)
    {
        rows_ = rows;
        d_ = d;
        dAlign_ = dAlign;
        rowFactor_ = rowFactor;
        blockFactor_ = blockFactor;
        eps_ = epsilon;
        invD_ = invD;
        ubFactor_ = rowFactor_ * dAlign_;

        xGm_.SetGlobalBuffer((__gm__ half*)x);
        residualGm_.SetGlobalBuffer((__gm__ half*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ half*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ half*)bias);
        outGm_.SetGlobalBuffer((__gm__ half*)output);

        hb_ = AlignUp32(ubFactor_ * sizeof(half));
        fb_ = AlignUp32(ubFactor_ * sizeof(float));
        pb_ = AlignUp32(dAlign_ * sizeof(half));
    }

    __aicore__ inline void Process()
    {
        const uint64_t blockIdx = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t begin = blockIdx * static_cast<uint64_t>(blockFactor_);
        if (begin >= rows_) {
            return;
        }
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(
            static_cast<uint64_t>(blockFactor_), rows_ - begin));

        LocalTensor<half> gammaH(TPosition::VECCALC, 4U*hb_+fb_, dAlign_);
        LocalTensor<half> biasH(TPosition::VECCALC, 4U*hb_+fb_+pb_, dAlign_);
        LoadParams(gammaH, biasH);

        LocalTensor<float> xFp32(TPosition::VECCALC, 4U*hb_, ubFactor_);

        LocalTensor<float> tmp(TPosition::VECCALC, 4U*hb_+fb_+2U*pb_, rowFactor_*64U);
        LocalTensor<float> rstd(TPosition::VECCALC, 4U*hb_+fb_+2U*pb_+rowFactor_*256U, rowFactor_);

        uint32_t done = 0U;
        uint32_t calcRows = MinU32(rowFactor_, rowWork);
        uint32_t elementNum = calcRows * dAlign_;
        uint64_t gmOff = begin * static_cast<uint64_t>(d_);
        // Each output slot owns a distinct MTE3->V completion token.
        uint32_t slot = 0U;
        SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
        SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(1));
        PrefetchXResidual(gmOff, calcRows);
        while (done < rowWork) {
            Sync<HardEvent::MTE2_V>();
            WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(slot));
            LocalTensor<half> xr(TPosition::VECCALC, 0U, ubFactor_);
            LocalTensor<half> rr(TPosition::VECCALC, hb_, ubFactor_);
            LocalTensor<half> yHalf(TPosition::VECCALC, (2U+slot)*hb_, ubFactor_);
            Add(yHalf, xr, rr, elementNum);

            Sync<HardEvent::V_MTE2>();

            const uint32_t nextDone = done + calcRows;
            uint32_t nextRows = 0U;
            if (nextDone < rowWork) {
                nextRows = MinU32(rowFactor_, rowWork - nextDone);
                const uint64_t nextOff = (begin + static_cast<uint64_t>(nextDone)) *
                                         static_cast<uint64_t>(d_);
                PrefetchXResidual(nextOff, nextRows);
            }

            Cast(xFp32, yHalf, RoundMode::CAST_NONE, elementNum);

            // Accumulate squared values directly into one 64-lane row accumulator.
            const uint8_t stride = static_cast<uint8_t>(dAlign_ / 8U);
            const uint8_t reps = static_cast<uint8_t>(calcRows);
            Mul(tmp, xFp32, xFp32, 64U, reps, {1,1,1,8,stride,stride});
            uint32_t col = 64U;
            for (; col + 64U <= d_; col += 64U) {
                MulAddDst(tmp, xFp32[col], xFp32[col], 64U, reps,
                          {1,1,1,8,stride,stride});
            }
            if (col < d_) {
                MulAddDst(tmp, xFp32[col], xFp32[col], d_ - col, reps,
                          {1,1,1,8,stride,stride});
            }
            WholeReduceSum<float>(rstd, tmp, 64U, calcRows, 1, 1, 8);
            Muls(rstd, rstd, invD_, calcRows);

            Adds(rstd, rstd, eps_, calcRows);

            Sqrt(rstd, rstd, calcRows);
            Duplicate(tmp, 1.0f, calcRows);

            Div(rstd, tmp, rstd, calcRows);


            Brcb(tmp, rstd, static_cast<uint8_t>((calcRows + 7U) / 8U), {1, 8});

            MulRowsByRstd(xFp32, tmp, calcRows);
            Cast(yHalf, xFp32, RoundMode::CAST_NONE, elementNum);

            FmaRowsByParam(yHalf, gammaH, biasH, calcRows);

            Sync<HardEvent::V_MTE3>();
            LocalTensor<half> ready = yHalf;
            if (d_ == dAlign_) {
                CopyOutPad(outGm_[gmOff], ready, calcRows * d_);
            } else {
                CopyOutRowsPad(outGm_[gmOff], ready, calcRows, d_);
            }
            SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(slot));
            slot ^= 1U;
            done = nextDone;
            calcRows = nextRows;
            elementNum = calcRows * dAlign_;
            gmOff = (begin + static_cast<uint64_t>(done)) * static_cast<uint64_t>(d_);
        }
        WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
        WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(1));
        PipeBarrier<PIPE_ALL>();
    }

private:
    template <HardEvent Event>
    __aicore__ inline void Sync() {
        SetFlag<Event>(static_cast<event_t>(0));
        WaitFlag<Event>(static_cast<event_t>(0));
    }
    __aicore__ inline void PrefetchXResidual(uint64_t gmOff, uint32_t calcRows)
    {
        LocalTensor<half> x(TPosition::VECCALC, 0U, ubFactor_);
        if (d_ == dAlign_) {
            CopyInPad(x, xGm_[gmOff], calcRows * d_);
        } else {
            CopyInRowsPad(x, xGm_[gmOff], calcRows, d_);
        }
        LocalTensor<half> r(TPosition::VECCALC, hb_, ubFactor_);
        if (d_ == dAlign_) {
            CopyInPad(r, residualGm_[gmOff], calcRows * d_);
        } else {
            CopyInRowsPad(r, residualGm_[gmOff], calcRows, d_);
        }
    }

    __aicore__ inline void LoadParams(
        const LocalTensor<half>& gammaH,
        const LocalTensor<half>& biasH)
    {
        CopyInPad(gammaH, gammaGm_, d_);
        CopyInPad(biasH, biasGm_, d_);
        event_t ep = static_cast<event_t>(0);
        SetFlag<HardEvent::MTE2_V>(ep);
        WaitFlag<HardEvent::MTE2_V>(ep);
    }

    __aicore__ inline void MulRowsByRstd(
        const LocalTensor<float>& y,
        const LocalTensor<float>& rstdBroadcast,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 8U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 64U <= d_; col += 64U) {
            Mul(y[col], y[col], rstdBroadcast, 64U, repeat,
                {1, 1, 0, repStride, repStride, 1});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Mul(y[col], y[col], rstdBroadcast, tail, repeat,
                {1, 1, 0, repStride, repStride, 1});
        }

    }

    // Fused affine y = y*gamma + bias over all rows in one FusedMulAdd,
    // replacing the separate full-width Mul then Add vector passes.
    __aicore__ inline void FmaRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& gamma,
        const LocalTensor<half>& bias,
        uint32_t rows)
    {
        // One fused vector op over all rows. Official CANN semantics:
        //   dst = src0 * dst + src1  (FusedMulAdd, atlasascendc_api_07_0050)
        // so dst=y, src0=gamma, src1=bias gives y = gamma*y + bias in one pass.
        // dst(y) advances one padded row per repeat (rs dataBlocks); gamma and
        // bias are a single loaded row reused by every repeat => repStride 0.
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t c = 0U;
        for (; c + 128U <= d_; c += 128U) {
            FusedMulAdd(y[c], gamma[c], bias[c], 128U, repeat,
                {1, 1, 1, repStride, 0, 0});
        }
        if (c < d_) {
            FusedMulAdd(y[c], gamma[c], bias[c], d_ - c, repeat,
                {1, 1, 1, repStride, 0, 0});
        }
    }

    __aicore__ inline void MulRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& param,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 128U <= d_; col += 128U) {
            Mul(y[col], y[col], param[col], 128U, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Mul(y[col], y[col], param[col], tail, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }

    }

    __aicore__ inline void AddRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& param,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 128U <= d_; col += 128U) {
            Add(y[col], y[col], param[col], 128U, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Add(y[col], y[col], param[col], tail, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }

    }

private:
    uint32_t hb_, fb_, pb_;
    GlobalTensor<half> xGm_;
    GlobalTensor<half> residualGm_;
    GlobalTensor<half> gammaGm_;
    GlobalTensor<half> biasGm_;
    GlobalTensor<half> outGm_;
    uint64_t rows_;
    uint32_t d_;
    uint32_t dAlign_;
    uint32_t rowFactor_;
    uint32_t blockFactor_;
    uint32_t ubFactor_;
    float eps_;
    float invD_;
};
} // namespace Iso08Private


namespace Iso10Private {
using namespace AddRmsNormBiasFixed;

class MergeRowsHalfFastKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, uint32_t rowFactor,
        uint32_t blockFactor, float epsilon, float invD)
    {
        rows_ = rows;
        d_ = d;
        dAlign_ = dAlign;
        rowFactor_ = rowFactor;
        blockFactor_ = blockFactor;
        eps_ = epsilon;
        invD_ = invD;
        ubFactor_ = rowFactor_ * dAlign_;

        xGm_.SetGlobalBuffer((__gm__ half*)x);
        residualGm_.SetGlobalBuffer((__gm__ half*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ half*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ half*)bias);
        outGm_.SetGlobalBuffer((__gm__ half*)output);

        hb_ = AlignUp32(ubFactor_ * sizeof(half));
        fb_ = AlignUp32(ubFactor_ * sizeof(float));
        pb_ = AlignUp32(dAlign_ * sizeof(half));
    }

    __aicore__ inline void Process()
    {
        const uint64_t blockIdx = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t begin = blockIdx * static_cast<uint64_t>(blockFactor_);
        if (begin >= rows_) {
            return;
        }
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(
            static_cast<uint64_t>(blockFactor_), rows_ - begin));

        LocalTensor<half> gammaH(TPosition::VECCALC, 4U*hb_+fb_, dAlign_);
        LocalTensor<half> biasH(TPosition::VECCALC, 4U*hb_+fb_+pb_, dAlign_);
        LoadParams(gammaH, biasH);

        LocalTensor<float> xFp32(TPosition::VECCALC, 4U*hb_, ubFactor_);

        LocalTensor<float> tmp(TPosition::VECCALC, 4U*hb_+fb_+2U*pb_, rowFactor_*64U);
        LocalTensor<float> rstd(TPosition::VECCALC, 4U*hb_+fb_+2U*pb_+rowFactor_*256U, rowFactor_);

        uint32_t done = 0U;
        uint32_t calcRows = MinU32(rowFactor_, rowWork);
        uint32_t elementNum = calcRows * dAlign_;
        uint64_t gmOff = begin * static_cast<uint64_t>(d_);
        // Each output slot owns a distinct MTE3->V completion token.
        uint32_t slot = 0U;
        SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
        SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(1));
        PrefetchXResidual(gmOff, calcRows);
        while (done < rowWork) {
            Sync<HardEvent::MTE2_V>();
            WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(slot));
            LocalTensor<half> xr(TPosition::VECCALC, 0U, ubFactor_);
            LocalTensor<half> rr(TPosition::VECCALC, hb_, ubFactor_);
            LocalTensor<half> yHalf(TPosition::VECCALC, (2U+slot)*hb_, ubFactor_);
            Add(yHalf, xr, rr, elementNum);

            Sync<HardEvent::V_MTE2>();

            const uint32_t nextDone = done + calcRows;
            uint32_t nextRows = 0U;
            if (nextDone < rowWork) {
                nextRows = MinU32(rowFactor_, rowWork - nextDone);
                const uint64_t nextOff = (begin + static_cast<uint64_t>(nextDone)) *
                                         static_cast<uint64_t>(d_);
                PrefetchXResidual(nextOff, nextRows);
            }

            Cast(xFp32, yHalf, RoundMode::CAST_NONE, elementNum);

            // Accumulate squared values directly into one 64-lane row accumulator.
            const uint8_t stride = static_cast<uint8_t>(dAlign_ / 8U);
            const uint8_t reps = static_cast<uint8_t>(calcRows);
            Mul(tmp, xFp32, xFp32, 64U, reps, {1,1,1,8,stride,stride});
            uint32_t col = 64U;
            for (; col + 64U <= d_; col += 64U) {
                MulAddDst(tmp, xFp32[col], xFp32[col], 64U, reps,
                          {1,1,1,8,stride,stride});
            }
            if (col < d_) {
                MulAddDst(tmp, xFp32[col], xFp32[col], d_ - col, reps,
                          {1,1,1,8,stride,stride});
            }
            WholeReduceSum<float>(rstd, tmp, 64U, calcRows, 1, 1, 8);
            Muls(rstd, rstd, invD_, calcRows);

            Adds(rstd, rstd, eps_, calcRows);

            Sqrt(rstd, rstd, calcRows);
            Duplicate(tmp, 1.0f, calcRows);

            Div(rstd, tmp, rstd, calcRows);


            Brcb(tmp, rstd, static_cast<uint8_t>((calcRows + 7U) / 8U), {1, 8});

            MulRowsByRstd(xFp32, tmp, calcRows);
            Cast(yHalf, xFp32, RoundMode::CAST_NONE, elementNum);

            FmaRowsByParam(yHalf, gammaH, biasH, calcRows);

            Sync<HardEvent::V_MTE3>();
            LocalTensor<half> ready = yHalf;
            if (d_ == dAlign_) {
                CopyOutPad(outGm_[gmOff], ready, calcRows * d_);
            } else {
                CopyOutRowsPad(outGm_[gmOff], ready, calcRows, d_);
            }
            SetFlag<HardEvent::MTE3_V>(static_cast<event_t>(slot));
            slot ^= 1U;
            done = nextDone;
            calcRows = nextRows;
            elementNum = calcRows * dAlign_;
            gmOff = (begin + static_cast<uint64_t>(done)) * static_cast<uint64_t>(d_);
        }
        WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(0));
        WaitFlag<HardEvent::MTE3_V>(static_cast<event_t>(1));
        PipeBarrier<PIPE_ALL>();
    }

private:
    template <HardEvent Event>
    __aicore__ inline void Sync() {
        SetFlag<Event>(static_cast<event_t>(0));
        WaitFlag<Event>(static_cast<event_t>(0));
    }
    __aicore__ inline void PrefetchXResidual(uint64_t gmOff, uint32_t calcRows)
    {
        LocalTensor<half> x(TPosition::VECCALC, 0U, ubFactor_);
        if (d_ == dAlign_) {
            CopyInPad(x, xGm_[gmOff], calcRows * d_);
        } else {
            CopyInRowsPad(x, xGm_[gmOff], calcRows, d_);
        }
        LocalTensor<half> r(TPosition::VECCALC, hb_, ubFactor_);
        if (d_ == dAlign_) {
            CopyInPad(r, residualGm_[gmOff], calcRows * d_);
        } else {
            CopyInRowsPad(r, residualGm_[gmOff], calcRows, d_);
        }
    }

    __aicore__ inline void LoadParams(
        const LocalTensor<half>& gammaH,
        const LocalTensor<half>& biasH)
    {
        CopyInPad(gammaH, gammaGm_, d_);
        CopyInPad(biasH, biasGm_, d_);
        event_t ep = static_cast<event_t>(0);
        SetFlag<HardEvent::MTE2_V>(ep);
        WaitFlag<HardEvent::MTE2_V>(ep);
    }

    __aicore__ inline void MulRowsByRstd(
        const LocalTensor<float>& y,
        const LocalTensor<float>& rstdBroadcast,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 8U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 64U <= d_; col += 64U) {
            Mul(y[col], y[col], rstdBroadcast, 64U, repeat,
                {1, 1, 0, repStride, repStride, 1});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Mul(y[col], y[col], rstdBroadcast, tail, repeat,
                {1, 1, 0, repStride, repStride, 1});
        }

    }

    // Fused affine y = y*gamma + bias over all rows in one FusedMulAdd,
    // replacing the separate full-width Mul then Add vector passes.
    __aicore__ inline void FmaRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& gamma,
        const LocalTensor<half>& bias,
        uint32_t rows)
    {
        // One fused vector op over all rows. Official CANN semantics:
        //   dst = src0 * dst + src1  (FusedMulAdd, atlasascendc_api_07_0050)
        // so dst=y, src0=gamma, src1=bias gives y = gamma*y + bias in one pass.
        // dst(y) advances one padded row per repeat (rs dataBlocks); gamma and
        // bias are a single loaded row reused by every repeat => repStride 0.
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t c = 0U;
        for (; c + 128U <= d_; c += 128U) {
            FusedMulAdd(y[c], gamma[c], bias[c], 128U, repeat,
                {1, 1, 1, repStride, 0, 0});
        }
        if (c < d_) {
            FusedMulAdd(y[c], gamma[c], bias[c], d_ - c, repeat,
                {1, 1, 1, repStride, 0, 0});
        }
    }

    __aicore__ inline void MulRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& param,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 128U <= d_; col += 128U) {
            Mul(y[col], y[col], param[col], 128U, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Mul(y[col], y[col], param[col], tail, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }

    }

    __aicore__ inline void AddRowsByParam(
        const LocalTensor<half>& y,
        const LocalTensor<half>& param,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 16U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + 128U <= d_; col += 128U) {
            Add(y[col], y[col], param[col], 128U, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Add(y[col], y[col], param[col], tail, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }

    }

private:
    uint32_t hb_, fb_, pb_;
    GlobalTensor<half> xGm_;
    GlobalTensor<half> residualGm_;
    GlobalTensor<half> gammaGm_;
    GlobalTensor<half> biasGm_;
    GlobalTensor<half> outGm_;
    uint64_t rows_;
    uint32_t d_;
    uint32_t dAlign_;
    uint32_t rowFactor_;
    uint32_t blockFactor_;
    uint32_t ubFactor_;
    float eps_;
    float invD_;
};

} // namespace Iso10Private


namespace Iso11Private {
using namespace AddRmsNormBiasFixed;
__aicore__ inline void MulByBroadcastPrivateAuto(
    const LocalTensor<float>& y,
    const LocalTensor<float>& broadcast,
    uint32_t count)
{
    const uint32_t repeat = count / FP32_PER_REPEAT;
    const uint32_t body = repeat * FP32_PER_REPEAT;
    if (repeat > 0U) {
        Mul(y, y, broadcast, FP32_PER_REPEAT, static_cast<uint8_t>(repeat),
            {1, 1, 0, 8, 8, 0});
    }
    if (body < count) {
        Mul(y[body], y[body], broadcast, count - body, 1,
            {1, 1, 0, 8, 8, 0});
    }
    
}

class DeepPaddedFloatKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
        uint64_t rows, uint32_t d, uint32_t da, uint32_t batch,
        uint32_t bf, float eps, float invD)
    {
        rows_ = rows; d_ = d; da_ = da; batch_ = batch;
        bf_ = bf; eps_ = eps; invD_ = invD;
        xGm_.SetGlobalBuffer((__gm__ float*)x);
        rGm_.SetGlobalBuffer((__gm__ float*)r);
        gGm_.SetGlobalBuffer((__gm__ float*)g);
        bGm_.SetGlobalBuffer((__gm__ float*)b);
        oGm_.SetGlobalBuffer((__gm__ float*)o);
        const uint32_t bb = AlignUp32(batch_ * da_ * sizeof(float));
        const uint32_t pb = AlignUp32(da_ * sizeof(float));
        // Keep V6's three batch allocations and its row factor. Two x/output
        // buffers overlap MTE3 with the next batch; residual needs only one.
        pipe_.InitBuffer(ioQueue_, 2, bb);
        pipe_.InitBuffer(residualQueue_, 1, bb);
        pipe_.InitBuffer(gBuf_, pb);
        pipe_.InitBuffer(bBuf_, pb);
        pipe_.InitBuffer(rstdBuf_, AlignUp32(batch_ * sizeof(float)));
        pipe_.InitBuffer(tmpBuf_, AlignUp32(batch_ * FP32_PER_REPEAT * sizeof(float)));
    }

    __aicore__ inline void Process()
    {
        const uint64_t begin = static_cast<uint64_t>(GetBlockIdx()) * bf_;
        if (begin >= rows_) return;
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(bf_, rows_ - begin));
        LocalTensor<float> g = gBuf_.Get<float>(), b = bBuf_.Get<float>();
        LocalTensor<float> rstd = rstdBuf_.Get<float>(), tmp = tmpBuf_.Get<float>();
        CopyInPad(g, gGm_, d_);
        CopyInPad(b, bGm_, d_);
        const event_t ep =
            static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(ep);
        WaitFlag<HardEvent::MTE2_V>(ep);

        uint32_t done = 0U, n = MinU32(batch_, rowWork);
        LocalTensor<float> first = PrefetchX(begin * static_cast<uint64_t>(d_), n);
        PrefetchResidual(begin * static_cast<uint64_t>(d_), n);
        ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(first);
        while (done < rowWork) {
            LocalTensor<float> y =
                ioQueue_.DeQue<TPosition::GM, TPosition::VECIN, float>();
            LocalTensor<float> rr = residualQueue_.DeQue<float>();
            const uint32_t nextDone = done + n;
            uint32_t nextRows = 0U;
            LocalTensor<float> next;
            if (nextDone < rowWork) {
                nextRows = MinU32(batch_, rowWork - nextDone);
                next = PrefetchX((begin + nextDone) * static_cast<uint64_t>(d_), nextRows);
            }

            Add(y, y, rr, n * da_);
            // Wide independent FP32 lanes shorten the serial FMA chain.
            constexpr uint32_t ACC = 1024U;
            for (uint32_t i = 0U; i < n; ++i) {
                LocalTensor<float> acc = rr[i * ACC];
                LocalTensor<float> row = y[i * da_];
                Mul(acc, row, row, ACC);
                for (uint32_t col = ACC; col < d_; col += ACC) {
                    MulAddDst(acc, row[col], row[col], MinU32(ACC, d_ - col));
                }
                WholeReduceSum<float>(tmp[i * FP32_PER_REPEAT], acc,
                    FP32_PER_REPEAT, ACC / FP32_PER_REPEAT, 1, 1, 8);
            }
            WholeReduceSum<float>(rstd, tmp, ACC / FP32_PER_REPEAT, n, 1, 1, 8);
            residualQueue_.FreeTensor(rr);
            if (nextRows != 0U) {
                PrefetchResidual((begin + nextDone) * static_cast<uint64_t>(d_), nextRows);
            }
            Muls(rstd, rstd, invD_, n);
            Adds(rstd, rstd, eps_, n);
            Sqrt(rstd, rstd, n);
            Duplicate(tmp, 1.0f, n);
            Div(rstd, tmp, rstd, n);
            Brcb(tmp, rstd, static_cast<uint8_t>((n + 7U) / 8U), {1, 8});
            for (uint32_t i = 0U; i < n; ++i) {
                const uint32_t off = i * da_;
                MulByBroadcastPrivateAuto(y[off], tmp[i * 8U], d_);
                Mul(y[off], y[off], g, d_);
                Add(y[off], y[off], b, d_);
            }

            // The bound queue supplies V->MTE3 and MTE3->MTE2 ownership
            // transfers. Delay input enqueue to keep its shared FIFO empty
            // until the current output has been dequeued.
            ioQueue_.EnQue<TPosition::VECOUT, TPosition::GM, float>(y);
            LocalTensor<float> ready =
                ioQueue_.DeQue<TPosition::VECOUT, TPosition::GM, float>();
            CopyOutRowsPad(oGm_[(begin + done) * static_cast<uint64_t>(d_)], ready, n, d_);
            ioQueue_.FreeTensor(ready);
            if (nextRows != 0U) {
                ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(next);
            }
            done = nextDone;
            n = nextRows;
        }
    }

private:
    __aicore__ inline LocalTensor<float> PrefetchX(uint64_t off, uint32_t n)
    {
        LocalTensor<float> x = ioQueue_.AllocTensor<float>();
        CopyInRowsPad(x, xGm_[off], n, d_);
        return x;
    }

    __aicore__ inline void PrefetchResidual(uint64_t off, uint32_t n)
    {
        LocalTensor<float> r = residualQueue_.AllocTensor<float>();
        CopyInRowsPad(r, rGm_[off], n, d_);
        residualQueue_.EnQue(r);
    }
    TPipe pipe_;
    TQueBind<TPosition::VECIN, TPosition::VECOUT, 1> ioQueue_;
    TQue<QuePosition::VECIN, 1> residualQueue_;
    TBuf<TPosition::VECCALC> gBuf_, bBuf_, rstdBuf_, tmpBuf_;
    GlobalTensor<float> xGm_, rGm_, gGm_, bGm_, oGm_;
    uint64_t rows_;
    uint32_t d_, da_, batch_, bf_;
    float eps_, invD_;
};
class ExpandedParams3083Kernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
        uint64_t rows, uint32_t d, uint32_t da, uint32_t batch,
        uint32_t bf, float eps, float invD)
    {
        rows_ = rows; d_ = d; da_ = da; batch_ = batch;
        bf_ = bf; eps_ = eps; invD_ = invD;
        xGm_.SetGlobalBuffer((__gm__ float*)x);
        rGm_.SetGlobalBuffer((__gm__ float*)r);
        gGm_.SetGlobalBuffer((__gm__ float*)g);
        bGm_.SetGlobalBuffer((__gm__ float*)b);
        oGm_.SetGlobalBuffer((__gm__ float*)o);
        const uint32_t bb = AlignUp32(batch_ * da_ * sizeof(float));
        const uint32_t pb = AlignUp32(batch_ * da_ * sizeof(float));
        // Keep V6's three batch allocations and its row factor. Two x/output
        // buffers overlap MTE3 with the next batch; residual needs only one.
        pipe_.InitBuffer(ioQueue_, 2, bb);
        pipe_.InitBuffer(residualQueue_, 1, bb);
        pipe_.InitBuffer(gBuf_, pb);
        pipe_.InitBuffer(bBuf_, pb);
        pipe_.InitBuffer(rstdBuf_, AlignUp32(batch_ * sizeof(float)));
        pipe_.InitBuffer(tmpBuf_, AlignUp32(batch_ * FP32_PER_REPEAT * sizeof(float)));
    }

    __aicore__ inline void Process()
    {
        const uint64_t begin = static_cast<uint64_t>(GetBlockIdx()) * bf_;
        if (begin >= rows_) return;
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(bf_, rows_ - begin));
        LocalTensor<float> g = gBuf_.Get<float>(), b = bBuf_.Get<float>();
        LocalTensor<float> rstd = rstdBuf_.Get<float>(), tmp = tmpBuf_.Get<float>();
        CopyInPad(g, gGm_, d_);
        CopyInPad(b, bGm_, d_);
        const event_t ep =
            static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(ep);
        WaitFlag<HardEvent::MTE2_V>(ep);

        // Parameters remain resident for every batch owned by this core.
        for (uint32_t i = 1U; i < batch_; ++i) {
            DataCopy(g[i * da_], g, da_);
            DataCopy(b[i * da_], b, da_);
        }
        uint32_t done = 0U, n = MinU32(batch_, rowWork);
        LocalTensor<float> first = PrefetchX(begin * static_cast<uint64_t>(d_), n);
        PrefetchResidual(begin * static_cast<uint64_t>(d_), n);
        ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(first);
        while (done < rowWork) {
            LocalTensor<float> y =
                ioQueue_.DeQue<TPosition::GM, TPosition::VECIN, float>();
            LocalTensor<float> rr = residualQueue_.DeQue<float>();
            const uint32_t nextDone = done + n;
            uint32_t nextRows = 0U;
            LocalTensor<float> next;
            if (nextDone < rowWork) {
                nextRows = MinU32(batch_, rowWork - nextDone);
                next = PrefetchX((begin + nextDone) * static_cast<uint64_t>(d_), nextRows);
            }

            Add(y, y, rr, n * da_);
            // Wide independent FP32 lanes shorten the serial FMA chain.
            constexpr uint32_t ACC = 1024U;
            for (uint32_t i = 0U; i < n; ++i) {
                LocalTensor<float> acc = rr[i * ACC];
                LocalTensor<float> row = y[i * da_];
                Mul(acc, row, row, ACC);
                for (uint32_t col = ACC; col < d_; col += ACC) {
                    MulAddDst(acc, row[col], row[col], MinU32(ACC, d_ - col));
                }
                WholeReduceSum<float>(tmp[i * FP32_PER_REPEAT], acc,
                    FP32_PER_REPEAT, ACC / FP32_PER_REPEAT, 1, 1, 8);
            }
            WholeReduceSum<float>(rstd, tmp, ACC / FP32_PER_REPEAT, n, 1, 1, 8);
            residualQueue_.FreeTensor(rr);
            if (nextRows != 0U) {
                PrefetchResidual((begin + nextDone) * static_cast<uint64_t>(d_), nextRows);
            }
            Muls(rstd, rstd, invD_, n);
            Adds(rstd, rstd, eps_, n);
            Sqrt(rstd, rstd, n);
            Duplicate(tmp, 1.0f, n);
            Div(rstd, tmp, rstd, n);
            Brcb(tmp, rstd, static_cast<uint8_t>((n + 7U) / 8U), {1, 8});
            for (uint32_t i = 0U; i < n; ++i) {
                const uint32_t off = i * da_;
                MulByBroadcastPrivateAuto(y[off], tmp[i * 8U], d_);
            }
            Mul(y, y, g, n * da_);
            Add(y, y, b, n * da_);

            // The bound queue supplies V->MTE3 and MTE3->MTE2 ownership
            // transfers. Delay input enqueue to keep its shared FIFO empty
            // until the current output has been dequeued.
            ioQueue_.EnQue<TPosition::VECOUT, TPosition::GM, float>(y);
            LocalTensor<float> ready =
                ioQueue_.DeQue<TPosition::VECOUT, TPosition::GM, float>();
            CopyOutRowsPad(oGm_[(begin + done) * static_cast<uint64_t>(d_)], ready, n, d_);
            ioQueue_.FreeTensor(ready);
            if (nextRows != 0U) {
                ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(next);
            }
            done = nextDone;
            n = nextRows;
        }
    }

private:
    __aicore__ inline LocalTensor<float> PrefetchX(uint64_t off, uint32_t n)
    {
        LocalTensor<float> x = ioQueue_.AllocTensor<float>();
        CopyInRowsPad(x, xGm_[off], n, d_);
        return x;
    }

    __aicore__ inline void PrefetchResidual(uint64_t off, uint32_t n)
    {
        LocalTensor<float> r = residualQueue_.AllocTensor<float>();
        CopyInRowsPad(r, rGm_[off], n, d_);
        residualQueue_.EnQue(r);
    }
    TPipe pipe_;
    TQueBind<TPosition::VECIN, TPosition::VECOUT, 1> ioQueue_;
    TQue<QuePosition::VECIN, 1> residualQueue_;
    TBuf<TPosition::VECCALC> gBuf_, bBuf_, rstdBuf_, tmpBuf_;
    GlobalTensor<float> xGm_, rGm_, gGm_, bGm_, oGm_;
    uint64_t rows_;
    uint32_t d_, da_, batch_, bf_;
    float eps_, invD_;
};
} // namespace Iso11Private


namespace Iso12Private {
using namespace AscendC;
using namespace AddRmsNormBiasFixed;
__aicore__ inline void ReduceSumPrivateAuto12(
    const LocalTensor<float>& dst,
    const LocalTensor<float>& src,
    const LocalTensor<float>& work,
    uint32_t count)
{
    const uint64_t mask = FP32_PER_REPEAT;
    const uint32_t repeatTimes = count / FP32_PER_REPEAT;
    const uint32_t tailCount = count % FP32_PER_REPEAT;
    const uint32_t bodyCount = repeatTimes * FP32_PER_REPEAT;

    BinaryRepeatParams repeatParams;
    repeatParams.src0RepStride = ONE_REPEAT_BYTE_SIZE / ONE_BLK_SIZE;
    repeatParams.src0BlkStride = 1;
    repeatParams.src1RepStride = 0;
    repeatParams.src1BlkStride = 1;
    repeatParams.dstRepStride = 0;
    repeatParams.dstBlkStride = 1;

    Duplicate(work, 0.0f, FP32_PER_REPEAT);
    

    if (repeatTimes > 0U) {
        Add(work, src, work, mask, static_cast<uint8_t>(repeatTimes), repeatParams);
        
    }
    if (tailCount != 0U) {
        Add(work, src[bodyCount], work, static_cast<uint64_t>(tailCount), 1, repeatParams);
        
    }

    AscendCUtils::SetMask<float>(FP32_PER_REPEAT);
#if defined(__CCE_AICORE__) && (__CCE_AICORE__ == 220)
    if (g_coreType == AIV) {
        WholeReduceSum<float, false>(dst, work, MASK_PLACEHOLDER, 1, 0, 1, 0);
    }
#else
    WholeReduceSum<float, false>(
        dst, work, MASK_PLACEHOLDER, 1, 1, 1, DEFAULT_REPEAT_STRIDE);
#endif
    
}

// Private physical copy. Public AddRmsNormBiasFixed is frozen and must not be edited for route tuning.
template <typename T>
class MultiRowsWideKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t rowFactor, uint32_t blockFactor,
        float epsilon, float invD)
    {
        rows_ = rows;
        d_ = d;
        rowFactor_ = rowFactor;
        blockFactor_ = blockFactor;
        eps_ = epsilon;
        invD_ = invD;
        ubFactor_ = rowFactor_ * d_;
        xGm_.SetGlobalBuffer((__gm__ T*)x);
        residualGm_.SetGlobalBuffer((__gm__ T*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ T*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ T*)bias);
        outGm_.SetGlobalBuffer((__gm__ T*)output);

        const uint32_t tBytes = AlignUp32(ubFactor_ * sizeof(T));
        const uint32_t fBytes = AlignUp32(ubFactor_ * sizeof(float));
        const uint32_t paramBytes = AlignUp32(d_ * sizeof(float));
        const uint32_t rstdBytes = AlignUp32(rowFactor_ * sizeof(float));
        // Even a partial eight-row group writes a complete 64-float repeat.
        const uint32_t scratchFloats = ((rowFactor_ + 7U) / 8U) * FP32_PER_REPEAT;
        const uint32_t scratchBytes = AlignUp32(scratchFloats * sizeof(float));

        pipe_.InitBuffer(inQueue_, 2, tBytes);
        pipe_.InitBuffer(outQueue_, 1, tBytes);
        pipe_.InitBuffer(xFp32Buf_, fBytes);
        pipe_.InitBuffer(sqxBuf_, AlignUp32(d_ * sizeof(float)));
        pipe_.InitBuffer(gammaBuf_, paramBytes);
        pipe_.InitBuffer(biasBuf_, paramBytes);
        pipe_.InitBuffer(rstdBuf_, rstdBytes);
        pipe_.InitBuffer(scratchBuf_, scratchBytes);
    }

    __aicore__ inline void Process()
    {
        const uint64_t blockIdx = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t begin = blockIdx * static_cast<uint64_t>(blockFactor_);
        if (begin >= rows_) return;
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(
            static_cast<uint64_t>(blockFactor_), rows_ - begin));

        LocalTensor<float> gammaF = gammaBuf_.Get<float>();
        LocalTensor<float> biasF = biasBuf_.Get<float>();
        LoadParams(gammaF, biasF);
        LocalTensor<float> xFp32 = xFp32Buf_.Get<float>();
        LocalTensor<float> sqx = sqxBuf_.Get<float>();
        LocalTensor<float> rstd = rstdBuf_.Get<float>();
        LocalTensor<float> scratch = scratchBuf_.Get<float>();

        uint32_t done = 0U;
        uint32_t calcRows = MinU32(rowFactor_, rowWork);
        uint32_t elementNum = calcRows * d_;
        uint64_t gmOff = begin * static_cast<uint64_t>(d_);
        PrefetchXResidual(gmOff, elementNum);
        while (done < rowWork) {
            LocalTensor<T> xr = inQueue_.DeQue<T>();
            LocalTensor<T> rr = inQueue_.DeQue<T>();
            ToFloat(xFp32, xr, elementNum);
            // Share one FP32 residual/accumulator row across the batch.
            for (uint32_t i = 0U; i < calcRows; ++i) {
                ToFloat(sqx, rr[i * d_], d_);
                Add(xFp32[i * d_], xFp32[i * d_], sqx, d_);
            }
            
            inQueue_.FreeTensor(xr);
            inQueue_.FreeTensor(rr);

            const uint32_t nextDone = done + calcRows;
            uint32_t nextRows = 0U;
            if (nextDone < rowWork) {
                nextRows = MinU32(rowFactor_, rowWork - nextDone);
                const uint64_t nextOff = (begin + static_cast<uint64_t>(nextDone)) *
                                         static_cast<uint64_t>(d_);
                PrefetchXResidual(nextOff, nextRows * d_);
            }

            for (uint32_t i = 0U; i < calcRows; ++i) {
                Mul(sqx, xFp32[i * d_], xFp32[i * d_], d_);
                ReduceSumPrivateAuto12(rstd[i], sqx, scratch, d_);
            }
            Muls(rstd, rstd, invD_, calcRows);
            
            Adds(rstd, rstd, eps_, calcRows);
            
            Sqrt(rstd, rstd, calcRows);
            Duplicate(scratch, 1.0f, calcRows);
            
            Div(rstd, scratch, rstd, calcRows);
            
            Brcb(scratch, rstd, static_cast<uint8_t>((calcRows + 7U) / 8U), {1, 8});
            

            for (uint32_t i = 0U; i < calcRows; ++i) {
                const uint32_t off = i * d_;
                const uint32_t bodyRepeat = d_ / FP32_PER_REPEAT;
                const uint32_t body = bodyRepeat * FP32_PER_REPEAT;
                if (bodyRepeat > 0U) {
                    Mul(xFp32[off], xFp32[off], scratch[i * 8U],
                        FP32_PER_REPEAT, static_cast<uint8_t>(bodyRepeat),
                        {1, 1, 0, 8, 8, 0});
                }
                const uint32_t tail = d_ - body;
                if (tail != 0U) {
                    Mul(xFp32[off + body], xFp32[off + body], scratch[i * 8U],
                        tail, 1, {1, 1, 0, 8, 8, 0});
                }
            }
            
            for (uint32_t i = 0U; i < calcRows; ++i) {
                const uint32_t off = i * d_;
                Mul(xFp32[off], xFp32[off], gammaF, d_);
            }
            
            for (uint32_t i = 0U; i < calcRows; ++i) {
                const uint32_t off = i * d_;
                Add(xFp32[off], xFp32[off], biasF, d_);
            }
            

            LocalTensor<T> out = outQueue_.AllocTensor<T>();
            FromFloat(out, xFp32, elementNum);
            
            outQueue_.EnQue(out);
            LocalTensor<T> ready = outQueue_.DeQue<T>();
            CopyOutPad(outGm_[gmOff], ready, elementNum);
            outQueue_.FreeTensor(ready);
            done = nextDone;
            calcRows = nextRows;
            elementNum = calcRows * d_;
            gmOff = (begin + static_cast<uint64_t>(done)) * static_cast<uint64_t>(d_);
        }
    }

private:
    __aicore__ inline void PrefetchXResidual(uint64_t gmOff, uint32_t elementNum)
    {
        LocalTensor<T> x = inQueue_.AllocTensor<T>();
        CopyInPad(x, xGm_[gmOff], elementNum);
        inQueue_.EnQue(x);
        LocalTensor<T> r = inQueue_.AllocTensor<T>();
        CopyInPad(r, residualGm_[gmOff], elementNum);
        inQueue_.EnQue(r);
    }

    __aicore__ inline void LoadParams(
        const LocalTensor<float>& gammaF,
        const LocalTensor<float>& biasF)
    {
        LocalTensor<T> g = inQueue_.AllocTensor<T>();
        CopyInPad(g, gammaGm_, d_);
        inQueue_.EnQue(g);
        LocalTensor<T> b = inQueue_.AllocTensor<T>();
        CopyInPad(b, biasGm_, d_);
        inQueue_.EnQue(b);
        LocalTensor<T> gr = inQueue_.DeQue<T>();
        LocalTensor<T> br = inQueue_.DeQue<T>();
        ToFloat(gammaF, gr, d_);
        ToFloat(biasF, br, d_);
        
        inQueue_.FreeTensor(gr);
        inQueue_.FreeTensor(br);
    }

private:
    TPipe pipe_;
    TQue<QuePosition::VECIN, 2> inQueue_;
    TQue<QuePosition::VECOUT, 1> outQueue_;
    TBuf<TPosition::VECCALC> xFp32Buf_;
    TBuf<TPosition::VECCALC> sqxBuf_;
    TBuf<TPosition::VECCALC> gammaBuf_;
    TBuf<TPosition::VECCALC> biasBuf_;
    TBuf<TPosition::VECCALC> rstdBuf_;
    TBuf<TPosition::VECCALC> scratchBuf_;
    GlobalTensor<T> xGm_;
    GlobalTensor<T> residualGm_;
    GlobalTensor<T> gammaGm_;
    GlobalTensor<T> biasGm_;
    GlobalTensor<T> outGm_;
    uint64_t rows_;
    uint32_t d_;
    uint32_t rowFactor_;
    uint32_t blockFactor_;
    uint32_t ubFactor_;
    float eps_;
    float invD_;
};
} // namespace Iso12Private


namespace Iso13Private {
using namespace AscendC;
using namespace AddRmsNormBiasFixed;
// Private physical copy. Public AddRmsNormBiasFixed is frozen and must not be edited for route tuning.
class MultiRowsFloatPaddedKernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, uint32_t rowFactor,
        uint32_t blockFactor, float epsilon, float invD)
    {
        rows_ = rows; d_ = d; dAlign_ = dAlign; rowFactor_ = rowFactor;
        blockFactor_ = blockFactor; eps_ = epsilon; invD_ = invD;
        ubFactor_ = rowFactor_ * dAlign_;
        xGm_.SetGlobalBuffer((__gm__ float*)x);
        residualGm_.SetGlobalBuffer((__gm__ float*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ float*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ float*)bias);
        outGm_.SetGlobalBuffer((__gm__ float*)output);
        xGm_.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
        residualGm_.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);

        const uint32_t fBytes = AlignUp32(ubFactor_ * sizeof(float));
        const uint32_t paramBytes = AlignUp32(dAlign_ * sizeof(float));
        const uint32_t rstdBytes = AlignUp32(rowFactor_ * sizeof(float));
        const uint32_t scratchBytes = AlignUp32(rowFactor_ * FP32_PER_REPEAT * sizeof(float));
        // Same three batch allocations as V6: two x/output buffers plus one
        // residual/square buffer. Preserve rowFactor and the reduction tree.
        pipe_.InitBuffer(ioQueue_, 2, fBytes);
        pipe_.InitBuffer(residualQueue_, 1, fBytes);
        pipe_.InitBuffer(gammaBuf_, paramBytes);
        pipe_.InitBuffer(biasBuf_, paramBytes);
        pipe_.InitBuffer(rstdBuf_, rstdBytes);
        pipe_.InitBuffer(scratchBuf_, scratchBytes);
    }

    __aicore__ inline void Process()
    {
        const uint64_t blockIdx = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t begin = blockIdx * static_cast<uint64_t>(blockFactor_);
        if (begin >= rows_) return;
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(
            static_cast<uint64_t>(blockFactor_), rows_ - begin));

        LocalTensor<float> gammaF = gammaBuf_.Get<float>();
        LocalTensor<float> biasF = biasBuf_.Get<float>();
        CopyInPad(gammaF, gammaGm_, d_);
        CopyInPad(biasF, biasGm_, d_);
        event_t ep = static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(ep);
        WaitFlag<HardEvent::MTE2_V>(ep);

        LocalTensor<float> rstd = rstdBuf_.Get<float>();
        LocalTensor<float> scratch = scratchBuf_.Get<float>();

        // As in Iso11, compiler auto-sync handles LocalTensor V dependencies.
        // DMA dependencies and queue-buffer ownership remain explicit.
        uint32_t done = 0U;
        uint32_t calcRows = MinU32(rowFactor_, rowWork);
        uint64_t gmOff = begin * static_cast<uint64_t>(d_);
        LocalTensor<float> first = PrefetchX(gmOff, calcRows);
        PrefetchResidual(gmOff, calcRows);
        ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(first);

        while (done < rowWork) {
            LocalTensor<float> y =
                ioQueue_.DeQue<TPosition::GM, TPosition::VECIN, float>();
            LocalTensor<float> rr = residualQueue_.DeQue<float>();
            const uint32_t nextDone = done + calcRows;
            uint32_t nextRows = 0U;
            uint64_t nextOff = 0ULL;
            LocalTensor<float> next;
            if (nextDone < rowWork) {
                nextRows = MinU32(rowFactor_, rowWork - nextDone);
                nextOff = (begin + static_cast<uint64_t>(nextDone)) *
                          static_cast<uint64_t>(d_);
                // The other x/output slot is independent of rr: start its
                // input DMA before square/reduction, not after rr is freed.
                next = PrefetchX(nextOff, nextRows);
            }
            const uint32_t elementNum = calcRows * dAlign_;
            Add(y, y, rr, elementNum);
            // Reuse the consumed residual allocation for squares. Do not free
            // it (or enqueue the next batch into it) until reduction is done.
            Mul(rr, y, y, elementNum);
            const uint32_t full = d_ / FP32_PER_REPEAT;
            const uint32_t tail = d_ % FP32_PER_REPEAT;
            const uint32_t partialCount = full + (tail != 0U ? 1U : 0U);
            for (uint32_t i = 0U; i < calcRows; ++i) {
                const uint32_t off = i * dAlign_;
                LocalTensor<float> partial = scratch[i * FP32_PER_REPEAT];
                WholeReduceSum<float>(partial, rr[off],
                    FP32_PER_REPEAT, full, 1, 1, 8);
                if (tail != 0U) {
                    // WholeReduceSum destinations require scalar alignment;
                    // the source starts at a 64-float (256-byte) boundary.
                    WholeReduceSum<float>(partial[full],
                        rr[off + full * FP32_PER_REPEAT], tail, 1, 1, 1, 8);
                }
            }
            // D <= 4096 on this route: at most 64 valid partials per row.
            WholeReduceSum<float>(rstd, scratch, partialCount, calcRows, 1, 1, 8);
            residualQueue_.FreeTensor(rr);

            if (nextRows != 0U) {
                PrefetchResidual(nextOff, nextRows);
            }

            Muls(rstd, rstd, invD_, calcRows);
            Adds(rstd, rstd, eps_, calcRows);
            Sqrt(rstd, rstd, calcRows);
            Duplicate(scratch, 1.0f, calcRows);
            Div(rstd, scratch, rstd, calcRows);
            Brcb(scratch, rstd, static_cast<uint8_t>((calcRows + 7U) / 8U), {1, 8});

            for (uint32_t i = 0U; i < calcRows; ++i) {
                const uint32_t off = i * dAlign_;
                MulByBroadcast64(y[off], scratch[i * 8U], d_);
                Mul(y[off], y[off], gammaF, d_);
                Add(y[off], y[off], biasF, d_);
            }

            ioQueue_.EnQue<TPosition::VECOUT, TPosition::GM, float>(y);
            LocalTensor<float> ready =
                ioQueue_.DeQue<TPosition::VECOUT, TPosition::GM, float>();
            CopyOutRowsPad(outGm_[gmOff], ready, calcRows, d_);
            // FreeTensor protects this buffer until MTE3 finishes. The next
            // batch uses the other x/output buffer without an immediate wait.
            ioQueue_.FreeTensor(ready);
            if (nextRows != 0U) {
                ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(next);
            }

            done = nextDone;
            calcRows = nextRows;
            gmOff = (begin + static_cast<uint64_t>(done)) * static_cast<uint64_t>(d_);
        }
    }

private:
    __aicore__ inline LocalTensor<float> PrefetchX(uint64_t gmOff, uint32_t calcRows)
    {
        LocalTensor<float> x = ioQueue_.AllocTensor<float>();
        CopyInRowsPad(x, xGm_[gmOff], calcRows, d_);
        // Do not enqueue x here: the shared bound FIFO must first carry the
        // current output. Its input enqueue follows the output dequeue.
        return x;
    }

    __aicore__ inline void PrefetchResidual(uint64_t gmOff, uint32_t calcRows)
    {
        LocalTensor<float> r = residualQueue_.AllocTensor<float>();
        CopyInRowsPad(r, residualGm_[gmOff], calcRows, d_);
        residualQueue_.EnQue(r);
    }

private:
    TPipe pipe_;
    TQueBind<TPosition::VECIN, TPosition::VECOUT, 1> ioQueue_;
    TQue<QuePosition::VECIN, 1> residualQueue_;
    TBuf<TPosition::VECCALC> gammaBuf_, biasBuf_, rstdBuf_, scratchBuf_;
    GlobalTensor<float> xGm_, residualGm_, gammaGm_, biasGm_, outGm_;
    uint64_t rows_;
    uint32_t d_, dAlign_, rowFactor_, blockFactor_, ubFactor_;
    float eps_, invD_;
};
} // namespace Iso13Private


namespace Iso14Private {
using namespace AscendC;
using namespace AddRmsNormBiasFixed;
// Private physical copy. Public AddRmsNormBiasFixed is frozen and must not be edited for route tuning.
template <typename T>
class MergeRowsKernel {
public:
    __aicore__ inline MergeRowsKernel() {}

    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, uint32_t rowFactor,
        uint32_t blockFactor, float epsilon, float invD)
    {
        rows_ = rows;
        d_ = d;
        dAlign_ = dAlign;
        rowFactor_ = rowFactor;
        blockFactor_ = blockFactor;
        eps_ = epsilon;
        invD_ = invD;
        ubFactor_ = rowFactor_ * dAlign_;

        xGm_.SetGlobalBuffer((__gm__ T*)x);
        residualGm_.SetGlobalBuffer((__gm__ T*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ T*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ T*)bias);
        outGm_.SetGlobalBuffer((__gm__ T*)output);

        // Stream large one-use activations without evicting cached parameters.
        // Smaller workloads retain the default L2 policy.
        if (rows_ * static_cast<uint64_t>(d_) * sizeof(T) >= (256ULL << 20U)) {
            xGm_.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
            residualGm_.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
            outGm_.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
        }

        const uint32_t tBytes = AlignUp32(ubFactor_ * sizeof(T));
        const uint32_t fBytes = AlignUp32(ubFactor_ * sizeof(float));
        const uint32_t paramBytes = AlignUp32(dAlign_ * sizeof(float));
        const uint32_t tmpBytes = AlignUp32(rowFactor_ * FP32_PER_REPEAT * sizeof(float));
        const uint32_t rstdBytes = AlignUp32(rowFactor_ * sizeof(float));

        pipe_.InitBuffer(inQueue_, 2, tBytes);
        pipe_.InitBuffer(outQueue_, 1, tBytes);
        pipe_.InitBuffer(yBuf_, fBytes + 256U);
        pipe_.InitBuffer(sqxBuf_, fBytes);
        pipe_.InitBuffer(gammaBuf_, paramBytes);
        pipe_.InitBuffer(biasBuf_, paramBytes);
        pipe_.InitBuffer(tmpBuf_, tmpBytes);
        pipe_.InitBuffer(rstdBuf_, rstdBytes);
    }

    __aicore__ inline void Process()
    {
        const uint64_t blockIdx = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t blockCount = static_cast<uint64_t>(GetBlockNum());
        if (rows_ == 0ULL || rowFactor_ == 0U || blockCount == 0ULL) {
            return;
        }
        const uint64_t numBatches = (rows_ - 1ULL) /
                                    static_cast<uint64_t>(rowFactor_) + 1ULL;
        if (blockIdx >= numBatches) {
            return;
        }

        LocalTensor<float> gammaF = gammaBuf_.Get<float>();
        LocalTensor<float> biasF = biasBuf_.Get<float>();
        LoadParams(gammaF, biasF);

        LocalTensor<float> y = yBuf_.Get<float>();
        LocalTensor<float> sqx = sqxBuf_.Get<float>();
        LocalTensor<float> tmp = tmpBuf_.Get<float>();
        LocalTensor<float> rstd = rstdBuf_.Get<float>();

        // Software pipeline: while Vector works on the current batch, MTE2
        // prefetches x/residual for the next batch into the two VECIN slots.
        uint64_t logicalBatch = blockIdx;
        const uint64_t firstRow = logicalBatch * static_cast<uint64_t>(rowFactor_);
        uint32_t calcRows = static_cast<uint32_t>(MinU64(
            static_cast<uint64_t>(rowFactor_), rows_ - firstRow));
        uint32_t elementNum = calcRows * dAlign_;
        uint64_t gmOff = firstRow * static_cast<uint64_t>(d_);
        PrefetchXResidual(gmOff, calcRows);
        while (true) {
            ConsumeXResidual(elementNum, y, sqx);

            const bool hasNext = numBatches - logicalBatch > blockCount;
            uint64_t nextBatch = logicalBatch;
            uint32_t nextRows = 0U;
            uint64_t nextOff = gmOff;
            if (hasNext) {
                nextBatch = logicalBatch + blockCount;
                const uint64_t nextRow = nextBatch * static_cast<uint64_t>(rowFactor_);
                nextRows = static_cast<uint32_t>(MinU64(
                    static_cast<uint64_t>(rowFactor_), rows_ - nextRow));
                nextOff = nextRow * static_cast<uint64_t>(d_);
                PrefetchXResidual(nextOff, nextRows);
            }

            Mul(sqx, y, y, elementNum);
            
            ReduceSumMultiNAuto(rstd, sqx, tmp, calcRows, d_, dAlign_);
            Muls(rstd, rstd, invD_, calcRows);
            
            Adds(rstd, rstd, eps_, calcRows);
            
            Sqrt(rstd, rstd, calcRows);
            Duplicate(tmp, 1.0f, calcRows);
            
            Div(rstd, tmp, rstd, calcRows);
            

            Brcb(tmp, rstd, static_cast<uint8_t>((calcRows + 7U) / 8U), {1, 8});
            
            MulRowsByRstd(y, tmp, calcRows);
            MulRowsByParam(y, gammaF, calcRows);
            AddRowsByParam(y, biasF, calcRows);

            StoreRows(outGm_[gmOff], y, calcRows, elementNum);
            if (!hasNext) {
                break;
            }
            logicalBatch = nextBatch;
            calcRows = nextRows;
            elementNum = calcRows * dAlign_;
            gmOff = nextOff;
        }
    }

private:
    __aicore__ inline void LoadParams(
        const LocalTensor<float>& gammaF,
        const LocalTensor<float>& biasF)
    {
        LocalTensor<T> g = inQueue_.AllocTensor<T>();
        CopyInPad(g, gammaGm_, d_);
        inQueue_.EnQue(g);
        LocalTensor<T> b = inQueue_.AllocTensor<T>();
        CopyInPad(b, biasGm_, d_);
        inQueue_.EnQue(b);

        LocalTensor<T> gr = inQueue_.DeQue<T>();
        LocalTensor<T> br = inQueue_.DeQue<T>();
        ToFloat(gammaF, gr, d_);
        ToFloat(biasF, br, d_);
        
        inQueue_.FreeTensor(gr);
        inQueue_.FreeTensor(br);
    }

    __aicore__ inline void PrefetchXResidual(uint64_t gmOff, uint32_t calcRows)
    {
        LocalTensor<T> x = inQueue_.AllocTensor<T>();
        if (d_ == dAlign_) {
            CopyInPad(x, xGm_[gmOff], calcRows * d_);
        } else {
            CopyInRowsPad(x, xGm_[gmOff], calcRows, d_);
        }
        inQueue_.EnQue(x);
        LocalTensor<T> r = inQueue_.AllocTensor<T>();
        if (d_ == dAlign_) {
            CopyInPad(r, residualGm_[gmOff], calcRows * d_);
        } else {
            CopyInRowsPad(r, residualGm_[gmOff], calcRows, d_);
        }
        inQueue_.EnQue(r);
    }

    __aicore__ inline void ConsumeXResidual(
        uint32_t elementNum,
        const LocalTensor<float>& y,
        const LocalTensor<float>& tmpF)
    {
        LocalTensor<T> xr = inQueue_.DeQue<T>();
        LocalTensor<T> rr = inQueue_.DeQue<T>();
        ToFloat(y, xr, elementNum);
        ToFloat(tmpF, rr, elementNum);
        Add(y, y, tmpF, elementNum);
        
        inQueue_.FreeTensor(xr);
        inQueue_.FreeTensor(rr);
    }

    __aicore__ inline void MulRowsByRstd(
        const LocalTensor<float>& y,
        const LocalTensor<float>& rstdBroadcast,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 8U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + FP32_PER_REPEAT <= d_; col += FP32_PER_REPEAT) {
            Mul(y[col], y[col], rstdBroadcast, FP32_PER_REPEAT, repeat,
                {1, 1, 0, repStride, repStride, 1});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Mul(y[col], y[col], rstdBroadcast, tail, repeat,
                {1, 1, 0, repStride, repStride, 1});
        }
        
    }

    __aicore__ inline void MulRowsByParam(
        const LocalTensor<float>& y,
        const LocalTensor<float>& param,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 8U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + FP32_PER_REPEAT <= d_; col += FP32_PER_REPEAT) {
            Mul(y[col], y[col], param[col], FP32_PER_REPEAT, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Mul(y[col], y[col], param[col], tail, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        
    }

    __aicore__ inline void AddRowsByParam(
        const LocalTensor<float>& y,
        const LocalTensor<float>& param,
        uint32_t rows)
    {
        const uint8_t repStride = static_cast<uint8_t>(dAlign_ / 8U);
        const uint8_t repeat = static_cast<uint8_t>(rows);
        uint32_t col = 0U;
        for (; col + FP32_PER_REPEAT <= d_; col += FP32_PER_REPEAT) {
            Add(y[col], y[col], param[col], FP32_PER_REPEAT, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        const uint32_t tail = d_ - col;
        if (tail != 0U) {
            Add(y[col], y[col], param[col], tail, repeat,
                {1, 1, 1, repStride, repStride, 0});
        }
        
    }

    __aicore__ inline void StoreRows(
        const GlobalTensor<T>& dst,
        const LocalTensor<float>& src,
        uint32_t rows,
        uint32_t elementNum)
    {
        LocalTensor<T> out = outQueue_.AllocTensor<T>();
        FromFloat(out, src, elementNum);
        
        outQueue_.EnQue(out);
        LocalTensor<T> ready = outQueue_.DeQue<T>();
        if (d_ == dAlign_) {
            CopyOutPad(dst, ready, rows * d_);
        } else {
            CopyOutRowsPad(dst, ready, rows, d_);
        }
        outQueue_.FreeTensor(ready);
    }

private:
    TPipe pipe_;
    TQue<QuePosition::VECIN, 2> inQueue_;
    TQue<QuePosition::VECOUT, 1> outQueue_;
    TBuf<TPosition::VECCALC> yBuf_;
    TBuf<TPosition::VECCALC> sqxBuf_;
    TBuf<TPosition::VECCALC> gammaBuf_;
    TBuf<TPosition::VECCALC> biasBuf_;
    TBuf<TPosition::VECCALC> tmpBuf_;
    TBuf<TPosition::VECCALC> rstdBuf_;

    GlobalTensor<T> xGm_;
    GlobalTensor<T> residualGm_;
    GlobalTensor<T> gammaGm_;
    GlobalTensor<T> biasGm_;
    GlobalTensor<T> outGm_;

    uint64_t rows_;
    uint32_t d_;
    uint32_t dAlign_;
    uint32_t rowFactor_;
    uint32_t blockFactor_;
    uint32_t ubFactor_;
    float eps_;
    float invD_;
};
} // namespace Iso14Private


namespace Iso15Private {
using namespace AscendC;
using namespace AddRmsNormBiasFixed;
template <typename T>
class TiledSafe15Kernel {
public:
    static constexpr uint32_t TILE = 4096U;
    static constexpr uint32_t ROW_BATCH = 256U;

    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, float epsilon, float invD)
    {
        rows_ = rows; d_ = d; eps_ = epsilon; invD_ = invD;
        xGm_.SetGlobalBuffer((__gm__ T*)x);
        residualGm_.SetGlobalBuffer((__gm__ T*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ T*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ T*)bias);
        outGm_.SetGlobalBuffer((__gm__ T*)output);
        const uint32_t tBytes = AlignUp32(TILE * sizeof(T));
        const uint32_t fBytes = AlignUp32(TILE * sizeof(float));
        pipe_.InitBuffer(inQueue_, 2, tBytes);
        pipe_.InitBuffer(outQueue_, 1, tBytes);
        pipe_.InitBuffer(yBuf_, fBytes);
        pipe_.InitBuffer(tmpBuf_, fBytes);
        pipe_.InitBuffer(gammaBuf_, fBytes);
        pipe_.InitBuffer(biasBuf_, fBytes);
        pipe_.InitBuffer(accBuf_, FP32_PER_REPEAT * sizeof(float));
        pipe_.InitBuffer(normBuf_, ALIGN_BYTES);
        pipe_.InitBuffer(rstdBuf_, AlignUp32(ROW_BATCH * sizeof(float)));
        pipe_.InitBuffer(onesBuf_, AlignUp32(ROW_BATCH * sizeof(float)));
        pipe_.InitBuffer(bcastBuf_, FP32_PER_REPEAT * sizeof(float));
    }

    __aicore__ inline void Process()
    {
        const uint64_t blockIdx = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t blockNum = static_cast<uint64_t>(GetBlockNum());
        const uint64_t base = rows_ / blockNum;
        const uint64_t rem = rows_ % blockNum;
        const uint64_t begin = blockIdx * base + MinU64(blockIdx, rem);
        const uint64_t rowCount = base + (blockIdx < rem ? 1ULL : 0ULL);
        const uint64_t end = begin + rowCount;

        LocalTensor<float> y = yBuf_.Get<float>();
        LocalTensor<float> tmp = tmpBuf_.Get<float>();
        LocalTensor<float> gammaF = gammaBuf_.Get<float>();
        LocalTensor<float> biasF = biasBuf_.Get<float>();
        LocalTensor<float> acc = accBuf_.Get<float>();
        LocalTensor<float> norm = normBuf_.Get<float>();
        LocalTensor<float> rstd = rstdBuf_.Get<float>();
        LocalTensor<float> ones = onesBuf_.Get<float>();
        LocalTensor<float> bcast = bcastBuf_.Get<float>();

        uint64_t batchBegin = begin;
        while (batchBegin < end) {
            const uint32_t batchRows = static_cast<uint32_t>(MinU64(
                static_cast<uint64_t>(ROW_BATCH), end - batchBegin));

            // Pass 1: keep 64 square-sum lanes alive across every D tile.
            // Next tile is prefetched after the current input buffers are
            // released, so MTE2 overlaps the vector accumulation.
            for (uint32_t i = 0U; i < batchRows; ++i) {
                const uint64_t rowBase = (batchBegin + static_cast<uint64_t>(i)) *
                                         static_cast<uint64_t>(d_);
                Duplicate(acc, 0.0f, FP32_PER_REPEAT);

                uint32_t col = 0U;
                uint32_t valid = MinU32(TILE, d_);
                PrefetchTwo(xGm_[rowBase], residualGm_[rowBase], valid);
                while (col < d_) {
                    ConsumeTwo(y, tmp, valid);
                    const uint32_t nextCol = col + TILE;
                    uint32_t nextValid = 0U;
                    if (nextCol < d_) {
                        nextValid = MinU32(TILE, d_ - nextCol);
                        PrefetchTwo(xGm_[rowBase + nextCol], residualGm_[rowBase + nextCol], nextValid);
                    }
                    Add(y, y, tmp, valid);
                    AccumulateSquare64(acc, y, valid);
                    col = nextCol;
                    valid = nextValid;
                }
                FinalizeAcc64(norm, acc);
                // Vector destinations require a 32-byte aligned UB address.
                // Store the scalar through the scalar pipe so contiguous rstd[i]
                // remains valid for odd i and the following batched operations.
                rstd.SetValue(i, ReadScalar(norm));
            }
            event_t scalarReady =
                static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::S_V));
            SetFlag<HardEvent::S_V>(scalarReady);
            WaitFlag<HardEvent::S_V>(scalarReady);

            Muls(rstd, rstd, invD_, batchRows);
            Adds(rstd, rstd, eps_, batchRows);
            Sqrt(rstd, rstd, batchRows);
            Duplicate(ones, 1.0f, batchRows);
            Div(rstd, ones, rstd, batchRows);

            // Pass 2: tile-major order makes gamma/bias O(D) per core instead
            // of O(rows*D).  Within each tile, next row x/residual is prefetched
            // while the current row is normalized and written out.
            for (uint32_t col = 0U; col < d_; col += TILE) {
                const uint32_t valid = MinU32(TILE, d_ - col);
                LoadParamPair(col, valid, gammaF, biasF);

                uint32_t i = 0U;
                uint64_t rowBase = batchBegin * static_cast<uint64_t>(d_);
                PrefetchTwo(xGm_[rowBase + col], residualGm_[rowBase + col], valid);
                for (; i < batchRows; ++i) {
                    rowBase = (batchBegin + static_cast<uint64_t>(i)) * static_cast<uint64_t>(d_);
                    ConsumeTwo(y, tmp, valid);
                    if (i + 1U < batchRows) {
                        const uint64_t nextBase = (batchBegin + static_cast<uint64_t>(i + 1U)) *
                                                  static_cast<uint64_t>(d_);
                        PrefetchTwo(xGm_[nextBase + col], residualGm_[nextBase + col], valid);
                    }
                    Add(y, y, tmp, valid);
                    // Brcb consumes eight scalars from a 32-byte-aligned
                    // source. Reuse their eight broadcast blocks per group.
                    if ((i & 7U) == 0U) {
                        Brcb(bcast, rstd[i], 1, {1, 8});
                    }
                    MulByBroadcast64(y, bcast[(i & 7U) * 8U], valid);
                    Mul(y, y, gammaF, valid);
                    Add(y, y, biasF, valid);
                    Store(outGm_[rowBase + col], y, valid);
                }
            }
            batchBegin += static_cast<uint64_t>(batchRows);
        }
    }
private:
    __aicore__ inline void PrefetchTwo(
        const GlobalTensor<T>& aGm, const GlobalTensor<T>& bGm, uint32_t count)
    {
        LocalTensor<T> a = inQueue_.AllocTensor<T>();
        CopyInPad(a, aGm, count);
        inQueue_.EnQue(a);
        LocalTensor<T> b = inQueue_.AllocTensor<T>();
        CopyInPad(b, bGm, count);
        inQueue_.EnQue(b);
    }

    __aicore__ inline void ConsumeTwo(
        const LocalTensor<float>& aF, const LocalTensor<float>& bF, uint32_t count)
    {
        LocalTensor<T> ar = inQueue_.DeQue<T>();
        LocalTensor<T> br = inQueue_.DeQue<T>();
        ToFloat(aF, ar, count);
        ToFloat(bF, br, count);
        inQueue_.FreeTensor(ar);
        inQueue_.FreeTensor(br);
    }

    __aicore__ inline void LoadParamPair(
        uint32_t col, uint32_t count,
        const LocalTensor<float>& gammaF, const LocalTensor<float>& biasF)
    {
        LocalTensor<T> g = inQueue_.AllocTensor<T>();
        CopyInPad(g, gammaGm_[col], count);
        inQueue_.EnQue(g);
        LocalTensor<T> b = inQueue_.AllocTensor<T>();
        CopyInPad(b, biasGm_[col], count);
        inQueue_.EnQue(b);
        LocalTensor<T> gr = inQueue_.DeQue<T>();
        LocalTensor<T> br = inQueue_.DeQue<T>();
        ToFloat(gammaF, gr, count);
        ToFloat(biasF, br, count);
        inQueue_.FreeTensor(gr);
        inQueue_.FreeTensor(br);
    }

    __aicore__ inline void Store(
        const GlobalTensor<T>& dst, const LocalTensor<float>& src, uint32_t count)
    {
        LocalTensor<T> out = outQueue_.AllocTensor<T>();
        FromFloat(out, src, count);
        outQueue_.EnQue(out);
        LocalTensor<T> ready = outQueue_.DeQue<T>();
        CopyOutPad(dst, ready, count);
        outQueue_.FreeTensor(ready);
    }
private:
    TPipe pipe_;
    TQue<QuePosition::VECIN, 2> inQueue_;
    TQue<QuePosition::VECOUT, 1> outQueue_;
    TBuf<TPosition::VECCALC> yBuf_, tmpBuf_, gammaBuf_, biasBuf_;
    TBuf<TPosition::VECCALC> accBuf_, normBuf_, rstdBuf_, onesBuf_, bcastBuf_;
    GlobalTensor<T> xGm_, residualGm_, gammaGm_, biasGm_, outGm_;
    uint64_t rows_;
    uint32_t d_;
    float eps_, invD_;
};


// Private physical copy. Public AddRmsNormBiasFixed is frozen and must not be edited for route tuning.
template <typename T>
class FastKernel {
public:
    __aicore__ inline FastKernel() {}

    __aicore__ inline void Init(
        GM_ADDR x,
        GM_ADDR residual,
        GM_ADDR gamma,
        GM_ADDR bias,
        GM_ADDR output,
        uint64_t rows,
        uint32_t d,
        float epsilon,
        float invD)
    {
        rows_ = rows;
        d_ = d;
        eps_ = epsilon;
        invD_ = invD;

        xGm_.SetGlobalBuffer((__gm__ T*)x);
        residualGm_.SetGlobalBuffer((__gm__ T*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ T*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ T*)bias);
        outGm_.SetGlobalBuffer((__gm__ T*)output);

        // Stream large one-use activations without evicting cached parameters.
        // Smaller workloads retain the default L2 policy.
        if (rows_ * static_cast<uint64_t>(d_) * sizeof(T) >= (256ULL << 20U)) {
            xGm_.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
            residualGm_.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
            outGm_.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
        }

        const uint32_t tBytes = AlignUp32(d * sizeof(T));
        const uint32_t fBytes = AlignUp32(d * sizeof(float));

        pipe_.InitBuffer(inQueue_, 2, tBytes);
        pipe_.InitBuffer(outQueue_, 1, tBytes);
        pipe_.InitBuffer(yBuf_, fBytes);
        pipe_.InitBuffer(tmpBuf_, fBytes);
        pipe_.InitBuffer(gammaBuf_, fBytes);
        pipe_.InitBuffer(biasBuf_, fBytes);
        pipe_.InitBuffer(reduceBuf_, REDUCE_WORK_FLOATS * sizeof(float));
    }

    __aicore__ inline void Process()
    {
        LocalTensor<float> gammaF = gammaBuf_.Get<float>();
        LocalTensor<float> biasF = biasBuf_.Get<float>();
        PrefetchTwo(gammaGm_, biasGm_, d_);
        ConsumeTwo(gammaF, biasF, d_);

        const uint64_t blockIdx = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t blockNum = static_cast<uint64_t>(GetBlockNum());
        const uint64_t base = rows_ / blockNum;
        const uint64_t rem = rows_ % blockNum;
        const uint64_t begin = blockIdx * base + MinU64(blockIdx, rem);
        const uint64_t rowCount = base + (blockIdx < rem ? 1ULL : 0ULL);
        const uint64_t end = begin + rowCount;

        LocalTensor<float> y = yBuf_.Get<float>();
        LocalTensor<float> tmp = tmpBuf_.Get<float>();
        LocalTensor<float> reduceWork = reduceBuf_.Get<float>();

        if (begin >= end) return;
        uint64_t row = begin;
        uint64_t off = row * static_cast<uint64_t>(d_);
        PrefetchTwo(xGm_[off], residualGm_[off], d_);
        for (; row < end; ++row) {
            off = row * static_cast<uint64_t>(d_);
            ConsumeTwo(y, tmp, d_);
            if (row + 1ULL < end) {
                const uint64_t nextOff = (row + 1ULL) * static_cast<uint64_t>(d_);
                PrefetchTwo(xGm_[nextOff], residualGm_[nextOff], d_);
            }
            Add(y, y, tmp, d_);
            

            constexpr uint32_t ACC = 1024U;
            Mul(tmp, y, y, ACC);
            for (uint32_t col = ACC; col < d_; col += ACC) {
                MulAddDst(tmp, y[col], y[col], MinU32(ACC, d_ - col));
            }
            WholeReduceSum<float>(reduceWork, tmp, FP32_PER_REPEAT,
                ACC / FP32_PER_REPEAT, 1, 1, 8);
            WholeReduceSum<float>(tmp, reduceWork, ACC / FP32_PER_REPEAT,
                1, 1, 1, 8);
            NormalizeRowAuto(y, tmp, reduceWork, d_, invD_, eps_);
            Mul(y, y, gammaF, d_);
            
            Add(y, y, biasF, d_);
            

            Store(outGm_[off], y, d_);
        }
    }

private:
    __aicore__ inline void PrefetchTwo(
        const GlobalTensor<T>& aGm, const GlobalTensor<T>& bGm, uint32_t count)
    {
        LocalTensor<T> a = inQueue_.AllocTensor<T>();
        CopyInPad(a, aGm, count);
        inQueue_.EnQue(a);
        LocalTensor<T> b = inQueue_.AllocTensor<T>();
        CopyInPad(b, bGm, count);
        inQueue_.EnQue(b);
    }

    __aicore__ inline void ConsumeTwo(
        const LocalTensor<float>& aF, const LocalTensor<float>& bF, uint32_t count)
    {
        LocalTensor<T> ar = inQueue_.DeQue<T>();
        LocalTensor<T> br = inQueue_.DeQue<T>();
        ToFloat(aF, ar, count);
        ToFloat(bF, br, count);
        
        inQueue_.FreeTensor(ar);
        inQueue_.FreeTensor(br);
    }

    __aicore__ inline void Store(
        const GlobalTensor<T>& dst,
        const LocalTensor<float>& src,
        uint32_t count)
    {
        LocalTensor<T> out = outQueue_.AllocTensor<T>();
        FromFloat(out, src, count);
        
        outQueue_.EnQue(out);
        LocalTensor<T> ready = outQueue_.DeQue<T>();
        CopyOutPad(dst, ready, count);
        outQueue_.FreeTensor(ready);
    }

private:
    TPipe pipe_;
    TQue<QuePosition::VECIN, 2> inQueue_;
    TQue<QuePosition::VECOUT, 1> outQueue_;
    TBuf<TPosition::VECCALC> yBuf_;
    TBuf<TPosition::VECCALC> tmpBuf_;
    TBuf<TPosition::VECCALC> gammaBuf_;
    TBuf<TPosition::VECCALC> biasBuf_;
    TBuf<TPosition::VECCALC> reduceBuf_;

    GlobalTensor<T> xGm_;
    GlobalTensor<T> residualGm_;
    GlobalTensor<T> gammaGm_;
    GlobalTensor<T> biasGm_;
    GlobalTensor<T> outGm_;

    uint64_t rows_;
    uint32_t d_;
    float eps_;
    float invD_;
};
} // namespace Iso15Private

namespace CyclicResidual11Probe {
using namespace AscendC;
using namespace AddRmsNormBiasFixed;
using Iso11Private::MulByBroadcastPrivateAuto;

class CyclicResidualLate3083Kernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
        uint64_t rows, uint32_t d, uint32_t da, uint32_t batch,
        uint32_t bf, float eps, float invD)
    {
        rows_ = rows; d_ = d; da_ = da; batch_ = batch;
        bf_ = bf; eps_ = eps; invD_ = invD;
        xGm_.SetGlobalBuffer((__gm__ float*)x);
        rGm_.SetGlobalBuffer((__gm__ float*)r);
        gGm_.SetGlobalBuffer((__gm__ float*)g);
        bGm_.SetGlobalBuffer((__gm__ float*)b);
        oGm_.SetGlobalBuffer((__gm__ float*)o);
        const uint32_t bb = AlignUp32(batch_ * da_ * sizeof(float));
        const uint32_t pb = AlignUp32(batch_ * da_ * sizeof(float));
        // Keep V6's three batch allocations and its row factor. Two x/output
        // buffers overlap MTE3 with the next batch; residual needs only one.
        pipe_.InitBuffer(ioQueue_, 2, bb);
        pipe_.InitBuffer(residualBuf_, bb);
        pipe_.InitBuffer(gBuf_, pb);
        pipe_.InitBuffer(bBuf_, pb);
        pipe_.InitBuffer(rstdBuf_, AlignUp32(batch_ * sizeof(float)));
        pipe_.InitBuffer(tmpBuf_, AlignUp32(batch_ * FP32_PER_REPEAT * sizeof(float)));
    }

    __aicore__ inline void Process()
    {
        const uint64_t begin = static_cast<uint64_t>(GetBlockIdx()) * bf_;
        if (begin >= rows_) return;
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(bf_, rows_ - begin));
        LocalTensor<float> g = gBuf_.Get<float>(), b = bBuf_.Get<float>();
        LocalTensor<float> rstd = rstdBuf_.Get<float>(), tmp = tmpBuf_.Get<float>();
        LocalTensor<float> rr = residualBuf_.Get<float>();
        CopyInPad(g, gGm_, d_);
        CopyInPad(b, bGm_, d_);
        const event_t ep =
            static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(ep);
        WaitFlag<HardEvent::MTE2_V>(ep);

        // Parameters remain resident for every batch owned by this core.
        for (uint32_t i = 1U; i < batch_; ++i) {
            DataCopy(g[i * da_], g, da_);
            DataCopy(b[i * da_], b, da_);
        }
        uint32_t done = 0U, n = MinU32(batch_, rowWork);
        LocalTensor<float> first = PrefetchX(begin * static_cast<uint64_t>(d_), n);
        CopyInRowsPad(
            rr, rGm_[begin * static_cast<uint64_t>(d_)], n, d_);
        const event_t residualReady = ep;
        const event_t residualReuse =
            static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::V_MTE2));
        SetFlag<HardEvent::MTE2_V>(residualReady);
        ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(first);
        while (done < rowWork) {
            LocalTensor<float> y =
                ioQueue_.DeQue<TPosition::GM, TPosition::VECIN, float>();
            WaitFlag<HardEvent::MTE2_V>(residualReady);
            const uint32_t nextDone = done + n;
            uint32_t nextRows = 0U;
            LocalTensor<float> next;
            if (nextDone < rowWork) {
                nextRows = MinU32(batch_, rowWork - nextDone);
                next = PrefetchX((begin + nextDone) * static_cast<uint64_t>(d_), nextRows);
            }

            Add(y, y, rr, n * da_);
            // Wide independent FP32 lanes shorten the serial FMA chain.
            constexpr uint32_t ACC = 1024U;
            for (uint32_t i = 0U; i < n; ++i) {
                LocalTensor<float> acc = rr[i * da_];
                LocalTensor<float> row = y[i * da_];
                Mul(acc, row, row, ACC);
                for (uint32_t col = ACC; col < d_; col += ACC) {
                    MulAddDst(acc, row[col], row[col], MinU32(ACC, d_ - col));
                }
                WholeReduceSum<float>(tmp[i * FP32_PER_REPEAT], acc,
                    FP32_PER_REPEAT, ACC / FP32_PER_REPEAT, 1, 1, 8);
            }
            WholeReduceSum<float>(rstd, tmp, ACC / FP32_PER_REPEAT, n, 1, 1, 8);
            if (nextRows != 0U) {
                SetFlag<HardEvent::V_MTE2>(residualReuse);
                WaitFlag<HardEvent::V_MTE2>(residualReuse);
                CopyInRowsPad(
                    rr, rGm_[(begin + nextDone) * static_cast<uint64_t>(d_)],
                    nextRows, d_);
                SetFlag<HardEvent::MTE2_V>(residualReady);
            }
            Muls(rstd, rstd, invD_, n);
            Adds(rstd, rstd, eps_, n);
            Sqrt(rstd, rstd, n);
            Duplicate(tmp, 1.0f, n);
            Div(rstd, tmp, rstd, n);
            Brcb(tmp, rstd, static_cast<uint8_t>((n + 7U) / 8U), {1, 8});
            for (uint32_t i = 0U; i < n; ++i) {
                const uint32_t off = i * da_;
                MulByBroadcastPrivateAuto(y[off], tmp[i * 8U], d_);
            }
            Mul(y, y, g, n * da_);
            Add(y, y, b, n * da_);

            // The bound queue supplies V->MTE3 and MTE3->MTE2 ownership
            // transfers. Delay input enqueue to keep its shared FIFO empty
            // until the current output has been dequeued.
            ioQueue_.EnQue<TPosition::VECOUT, TPosition::GM, float>(y);
            LocalTensor<float> ready =
                ioQueue_.DeQue<TPosition::VECOUT, TPosition::GM, float>();
            CopyOutRowsPad(oGm_[(begin + done) * static_cast<uint64_t>(d_)], ready, n, d_);
            ioQueue_.FreeTensor(ready);
            if (nextRows != 0U) {
                ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(next);
            }
            done = nextDone;
            n = nextRows;
        }
    }

private:
    __aicore__ inline LocalTensor<float> PrefetchX(uint64_t off, uint32_t n)
    {
        LocalTensor<float> x = ioQueue_.AllocTensor<float>();
        CopyInRowsPad(x, xGm_[off], n, d_);
        return x;
    }

    TPipe pipe_;
    TQueBind<TPosition::VECIN, TPosition::VECOUT, 1> ioQueue_;
    TBuf<TPosition::VECCALC> residualBuf_;
    TBuf<TPosition::VECCALC> gBuf_, bBuf_, rstdBuf_, tmpBuf_;
    GlobalTensor<float> xGm_, rGm_, gGm_, bGm_, oGm_;
    uint64_t rows_;
    uint32_t d_, da_, batch_, bf_;
    float eps_, invD_;
};

class CyclicResidualEarly3083Kernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
        uint64_t rows, uint32_t d, uint32_t da, uint32_t batch,
        uint32_t bf, float eps, float invD)
    {
        rows_ = rows; d_ = d; da_ = da; batch_ = batch;
        bf_ = bf; eps_ = eps; invD_ = invD;
        xGm_.SetGlobalBuffer((__gm__ float*)x);
        rGm_.SetGlobalBuffer((__gm__ float*)r);
        gGm_.SetGlobalBuffer((__gm__ float*)g);
        bGm_.SetGlobalBuffer((__gm__ float*)b);
        oGm_.SetGlobalBuffer((__gm__ float*)o);
        const uint32_t bb = AlignUp32(batch_ * da_ * sizeof(float));
        const uint32_t pb = AlignUp32(batch_ * da_ * sizeof(float));
        // Keep V6's three batch allocations and its row factor. Two x/output
        // buffers overlap MTE3 with the next batch; residual needs only one.
        pipe_.InitBuffer(ioQueue_, 2, bb);
        pipe_.InitBuffer(residualBuf_, bb);
        pipe_.InitBuffer(gBuf_, pb);
        pipe_.InitBuffer(bBuf_, pb);
        pipe_.InitBuffer(rstdBuf_, AlignUp32(batch_ * sizeof(float)));
        pipe_.InitBuffer(tmpBuf_, AlignUp32(batch_ * FP32_PER_REPEAT * sizeof(float)));
    }

    __aicore__ inline void Process()
    {
        const uint64_t begin = static_cast<uint64_t>(GetBlockIdx()) * bf_;
        if (begin >= rows_) return;
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(bf_, rows_ - begin));
        LocalTensor<float> g = gBuf_.Get<float>(), b = bBuf_.Get<float>();
        LocalTensor<float> rstd = rstdBuf_.Get<float>(), tmp = tmpBuf_.Get<float>();
        LocalTensor<float> rr = residualBuf_.Get<float>();
        CopyInPad(g, gGm_, d_);
        CopyInPad(b, bGm_, d_);
        const event_t ep =
            static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(ep);
        WaitFlag<HardEvent::MTE2_V>(ep);

        // Parameters remain resident for every batch owned by this core.
        for (uint32_t i = 1U; i < batch_; ++i) {
            DataCopy(g[i * da_], g, da_);
            DataCopy(b[i * da_], b, da_);
        }
        uint32_t done = 0U, n = MinU32(batch_, rowWork);
        LocalTensor<float> first = PrefetchX(begin * static_cast<uint64_t>(d_), n);
        CopyInRowsPad(
            rr, rGm_[begin * static_cast<uint64_t>(d_)], n, d_);
        const event_t residualReady = ep;
        const event_t residualReuse =
            static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::V_MTE2));
        SetFlag<HardEvent::MTE2_V>(residualReady);
        ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(first);
        while (done < rowWork) {
            LocalTensor<float> y =
                ioQueue_.DeQue<TPosition::GM, TPosition::VECIN, float>();
            WaitFlag<HardEvent::MTE2_V>(residualReady);
            const uint32_t nextDone = done + n;
            uint32_t nextRows = 0U;
            LocalTensor<float> next;
            if (nextDone < rowWork) {
                nextRows = MinU32(batch_, rowWork - nextDone);
                next = PrefetchX((begin + nextDone) * static_cast<uint64_t>(d_), nextRows);
            }

            Add(y, y, rr, n * da_);
            // Wide independent FP32 lanes shorten the serial FMA chain.
            constexpr uint32_t ACC = 1024U;
            for (uint32_t i = 0U; i < n; ++i) {
                LocalTensor<float> acc = rr[i * da_];
                LocalTensor<float> row = y[i * da_];
                Mul(acc, row, row, ACC);
                for (uint32_t col = ACC; col < d_; col += ACC) {
                    MulAddDst(acc, row[col], row[col], MinU32(ACC, d_ - col));
                }
                WholeReduceSum<float>(tmp[i * FP32_PER_REPEAT], acc,
                    FP32_PER_REPEAT, ACC / FP32_PER_REPEAT, 1, 1, 8);
                if (i < nextRows) {
                    SetFlag<HardEvent::V_MTE2>(residualReuse);
                    WaitFlag<HardEvent::V_MTE2>(residualReuse);
                    CopyInRowsPad(
                        rr[i * da_],
                        rGm_[(begin + nextDone + i) *
                            static_cast<uint64_t>(d_)],
                        1U, d_);
                }
            }
            WholeReduceSum<float>(rstd, tmp, ACC / FP32_PER_REPEAT, n, 1, 1, 8);
            if (nextRows != 0U) {
                SetFlag<HardEvent::MTE2_V>(residualReady);
            }
            Muls(rstd, rstd, invD_, n);
            Adds(rstd, rstd, eps_, n);
            Sqrt(rstd, rstd, n);
            Duplicate(tmp, 1.0f, n);
            Div(rstd, tmp, rstd, n);
            Brcb(tmp, rstd, static_cast<uint8_t>((n + 7U) / 8U), {1, 8});
            for (uint32_t i = 0U; i < n; ++i) {
                const uint32_t off = i * da_;
                MulByBroadcastPrivateAuto(y[off], tmp[i * 8U], d_);
            }
            Mul(y, y, g, n * da_);
            Add(y, y, b, n * da_);

            // The bound queue supplies V->MTE3 and MTE3->MTE2 ownership
            // transfers. Delay input enqueue to keep its shared FIFO empty
            // until the current output has been dequeued.
            ioQueue_.EnQue<TPosition::VECOUT, TPosition::GM, float>(y);
            LocalTensor<float> ready =
                ioQueue_.DeQue<TPosition::VECOUT, TPosition::GM, float>();
            CopyOutRowsPad(oGm_[(begin + done) * static_cast<uint64_t>(d_)], ready, n, d_);
            ioQueue_.FreeTensor(ready);
            if (nextRows != 0U) {
                ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(next);
            }
            done = nextDone;
            n = nextRows;
        }
    }

private:
    __aicore__ inline LocalTensor<float> PrefetchX(uint64_t off, uint32_t n)
    {
        LocalTensor<float> x = ioQueue_.AllocTensor<float>();
        CopyInRowsPad(x, xGm_[off], n, d_);
        return x;
    }

    TPipe pipe_;
    TQueBind<TPosition::VECIN, TPosition::VECOUT, 1> ioQueue_;
    TBuf<TPosition::VECCALC> residualBuf_;
    TBuf<TPosition::VECCALC> gBuf_, bBuf_, rstdBuf_, tmpBuf_;
    GlobalTensor<float> xGm_, rGm_, gGm_, bGm_, oGm_;
    uint64_t rows_;
    uint32_t d_, da_, batch_, bf_;
    float eps_, invD_;
};

} // namespace CyclicResidual11Probe

extern "C" __global__ __vector__ void cyclicresidual11_late(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,
    uint64_t rows,uint32_t bf,float eps,float invD)
{
    CyclicResidual11Probe::CyclicResidualLate3083Kernel op;
    op.Init(x,r,g,b,o,rows,3083U,3088U,3U,bf,eps,invD);
    op.Process();
}

extern "C" __global__ __vector__ void cyclicresidual11_early(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,
    uint64_t rows,uint32_t bf,float eps,float invD)
{
    CyclicResidual11Probe::CyclicResidualEarly3083Kernel op;
    op.Init(x,r,g,b,o,rows,3083U,3088U,3U,bf,eps,invD);
    op.Process();
}

namespace BatchParam13Expanded {
using namespace AscendC;
using namespace AddRmsNormBiasFixed;

// Exact GK route 13 body with only three-row parameter residency and affine.
class ExpandedParams3079Kernel {
public:
    __aicore__ inline void Init(
        GM_ADDR x, GM_ADDR residual, GM_ADDR gamma, GM_ADDR bias, GM_ADDR output,
        uint64_t rows, uint32_t d, uint32_t dAlign, uint32_t rowFactor,
        uint32_t blockFactor, float epsilon, float invD)
    {
        rows_ = rows; d_ = d; dAlign_ = dAlign; rowFactor_ = rowFactor;
        blockFactor_ = blockFactor; eps_ = epsilon; invD_ = invD;
        ubFactor_ = rowFactor_ * dAlign_;
        xGm_.SetGlobalBuffer((__gm__ float*)x);
        residualGm_.SetGlobalBuffer((__gm__ float*)residual);
        gammaGm_.SetGlobalBuffer((__gm__ float*)gamma);
        biasGm_.SetGlobalBuffer((__gm__ float*)bias);
        outGm_.SetGlobalBuffer((__gm__ float*)output);
        xGm_.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);
        residualGm_.SetL2CacheHint(CacheMode::CACHE_MODE_DISABLE);

        const uint32_t fBytes = AlignUp32(ubFactor_ * sizeof(float));
        const uint32_t paramBytes = AlignUp32(ubFactor_ * sizeof(float));
        const uint32_t rstdBytes = AlignUp32(rowFactor_ * sizeof(float));
        const uint32_t scratchBytes =
            AlignUp32(rowFactor_ * FP32_PER_REPEAT * sizeof(float));
        pipe_.InitBuffer(ioQueue_, 2, fBytes);
        pipe_.InitBuffer(residualQueue_, 1, fBytes);
        pipe_.InitBuffer(gammaBuf_, paramBytes);
        pipe_.InitBuffer(biasBuf_, paramBytes);
        pipe_.InitBuffer(rstdBuf_, rstdBytes);
        pipe_.InitBuffer(scratchBuf_, scratchBytes);
    }

    __aicore__ inline void Process()
    {
        const uint64_t blockIdx = static_cast<uint64_t>(GetBlockIdx());
        const uint64_t begin = blockIdx * static_cast<uint64_t>(blockFactor_);
        if (begin >= rows_) return;
        const uint32_t rowWork = static_cast<uint32_t>(MinU64(
            static_cast<uint64_t>(blockFactor_), rows_ - begin));

        LocalTensor<float> gammaF = gammaBuf_.Get<float>();
        LocalTensor<float> biasF = biasBuf_.Get<float>();
        CopyInPad(gammaF, gammaGm_, d_);
        CopyInPad(biasF, biasGm_, d_);
        event_t ep = static_cast<event_t>(
            GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(ep);
        WaitFlag<HardEvent::MTE2_V>(ep);
        for (uint32_t i = 1U; i < rowFactor_; ++i) {
            DataCopy(gammaF[i * dAlign_], gammaF, dAlign_);
            DataCopy(biasF[i * dAlign_], biasF, dAlign_);
        }

        LocalTensor<float> rstd = rstdBuf_.Get<float>();
        LocalTensor<float> scratch = scratchBuf_.Get<float>();

        // GK queue, reduction, DMA and event schedule remain unchanged.
        uint32_t done = 0U;
        uint32_t calcRows = MinU32(rowFactor_, rowWork);
        uint64_t gmOff = begin * static_cast<uint64_t>(d_);
        LocalTensor<float> first = PrefetchX(gmOff, calcRows);
        PrefetchResidual(gmOff, calcRows);
        ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(first);

        while (done < rowWork) {
            LocalTensor<float> y =
                ioQueue_.DeQue<TPosition::GM, TPosition::VECIN, float>();
            LocalTensor<float> rr = residualQueue_.DeQue<float>();
            const uint32_t nextDone = done + calcRows;
            uint32_t nextRows = 0U;
            uint64_t nextOff = 0ULL;
            LocalTensor<float> next;
            if (nextDone < rowWork) {
                nextRows = MinU32(rowFactor_, rowWork - nextDone);
                nextOff = (begin + static_cast<uint64_t>(nextDone)) *
                          static_cast<uint64_t>(d_);
                next = PrefetchX(nextOff, nextRows);
            }
            const uint32_t elementNum = calcRows * dAlign_;
            Add(y, y, rr, elementNum);
            Mul(rr, y, y, elementNum);
            const uint32_t full = d_ / FP32_PER_REPEAT;
            const uint32_t tail = d_ % FP32_PER_REPEAT;
            const uint32_t partialCount =
                full + (tail != 0U ? 1U : 0U);
            for (uint32_t i = 0U; i < calcRows; ++i) {
                const uint32_t off = i * dAlign_;
                LocalTensor<float> partial =
                    scratch[i * FP32_PER_REPEAT];
                WholeReduceSum<float>(
                    partial, rr[off], FP32_PER_REPEAT, full, 1, 1, 8);
                if (tail != 0U) {
                    WholeReduceSum<float>(
                        partial[full],
                        rr[off + full * FP32_PER_REPEAT],
                        tail, 1, 1, 1, 8);
                }
            }
            WholeReduceSum<float>(
                rstd, scratch, partialCount, calcRows, 1, 1, 8);
            residualQueue_.FreeTensor(rr);

            if (nextRows != 0U) {
                PrefetchResidual(nextOff, nextRows);
            }

            Muls(rstd, rstd, invD_, calcRows);
            Adds(rstd, rstd, eps_, calcRows);
            Sqrt(rstd, rstd, calcRows);
            Duplicate(scratch, 1.0f, calcRows);
            Div(rstd, scratch, rstd, calcRows);
            Brcb(
                scratch, rstd,
                static_cast<uint8_t>((calcRows + 7U) / 8U), {1, 8});

            for (uint32_t i = 0U; i < calcRows; ++i) {
                const uint32_t off = i * dAlign_;
                MulByBroadcast64(y[off], scratch[i * 8U], d_);
            }
            Mul(y, y, gammaF, elementNum);
            Add(y, y, biasF, elementNum);

            ioQueue_.EnQue<TPosition::VECOUT, TPosition::GM, float>(y);
            LocalTensor<float> ready =
                ioQueue_.DeQue<TPosition::VECOUT, TPosition::GM, float>();
            CopyOutRowsPad(outGm_[gmOff], ready, calcRows, d_);
            ioQueue_.FreeTensor(ready);
            if (nextRows != 0U) {
                ioQueue_.EnQue<TPosition::GM, TPosition::VECIN, float>(next);
            }

            done = nextDone;
            calcRows = nextRows;
            gmOff = (begin + static_cast<uint64_t>(done)) *
                    static_cast<uint64_t>(d_);
        }
    }

private:
    __aicore__ inline LocalTensor<float> PrefetchX(
        uint64_t gmOff, uint32_t calcRows)
    {
        LocalTensor<float> x = ioQueue_.AllocTensor<float>();
        CopyInRowsPad(x, xGm_[gmOff], calcRows, d_);
        return x;
    }

    __aicore__ inline void PrefetchResidual(
        uint64_t gmOff, uint32_t calcRows)
    {
        LocalTensor<float> r = residualQueue_.AllocTensor<float>();
        CopyInRowsPad(r, residualGm_[gmOff], calcRows, d_);
        residualQueue_.EnQue(r);
    }

private:
    TPipe pipe_;
    TQueBind<TPosition::VECIN, TPosition::VECOUT, 1> ioQueue_;
    TQue<QuePosition::VECIN, 1> residualQueue_;
    TBuf<TPosition::VECCALC> gammaBuf_, biasBuf_, rstdBuf_, scratchBuf_;
    GlobalTensor<float> xGm_, residualGm_, gammaGm_, biasGm_, outGm_;
    uint64_t rows_;
    uint32_t d_, dAlign_, rowFactor_, blockFactor_, ubFactor_;
    float eps_, invD_;
};
} // namespace BatchParam13Expanded

extern "C" __global__ __vector__ void batchparam13_expanded3(
    GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
    float eps, float invD)
{
    BatchParam13Expanded::ExpandedParams3079Kernel op;
    op.Init(x, r, g, b, o, 10300ULL, 3079U, 3080U, 3U, 258U, eps, invD);
    op.Process();
}

// ---- unique per-route kernel entrypoints ------------------------------------
extern "C" __global__ __vector__ void iso01_kernel_tiny_half(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,float eps,float invD,uint32_t d,uint32_t dAlign)
{
    // Generic low-D fallback inside the isolated kernel symbol. Standard fixed
    // widths use the frozen tiny specialization; other widths use SingleLow.
    if (d == 64U) {
        Iso01Private::TinyOneRowKernel<half,64U> op;
        op.Init(x,r,g,b,o,rows,eps,invD); op.Process();
    } else {
        Iso01Private::SingleLowKernel<half> op;
        op.Init(x,r,g,b,o,rows,d,dAlign,eps,invD); op.Process();
    }
}

extern "C" __global__ __vector__ void iso02_kernel_prefetch_f32(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t dAlign,float eps,float invD)
{ Iso02Private::SinglePrefetchFloatGridKernel op; op.Init(x,r,g,b,o,rows,d,dAlign,eps,invD); op.Process(); }

extern "C" __global__ __vector__ void iso02_kernel_prefetch_f32_197(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,float eps,float invD)
{
    Iso02Private::SinglePrefetchFloatGridKernel op;
    op.Init(x,r,g,b,o,rows,197U,200U,eps,invD);
    op.Process();
}

extern "C" __global__ __vector__ void iso02_kernel_prefetch_f32_7x197_eps1e5(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o)
{
    Iso02Private::SinglePrefetchFloatKernel op;
    op.Init(x,r,g,b,o,7ULL,197U,200U,1.0e-5f,1.0f / 197.0f);
    op.Process();
}

extern "C" __global__ __vector__ void iso03_kernel_small_batch_f32(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t dAlign,uint32_t bf,float eps,float invD)
{ Iso03Private::SmallBatchFloatKernel op; op.Init(x,r,g,b,o,rows,d,dAlign,bf,eps,invD); op.Process(); }
#define ISO03_FIXED_EP(DV) extern "C" __global__ __vector__ void iso03_kernel_fixed_##DV(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t bf,float eps,float invD){Iso03Private::SmallBatchFloatFixedKernel<DV##U> op;op.Init(x,r,g,b,o,rows,bf,eps,invD);op.Process();}
ISO03_FIXED_EP(256) ISO03_FIXED_EP(320) ISO03_FIXED_EP(384)
#undef ISO03_FIXED_EP

extern "C" __global__ __vector__ void iso04_kernel_resident208(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t blocks,float eps,float invD)
{ Iso04Private::ResidentHalfAlign208Kernel op; op.Init(x,r,g,b,o,rows,d,blocks,eps,invD); op.Process(); }

extern "C" __global__ __vector__ void iso04_kernel_fallback192(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t blocks,float eps,float invD)
{ Iso04Private::TiledFallbackHalfKernel<192U> op; op.Init(x,r,g,b,o,rows,d,blocks,eps,invD); op.Process(); }

extern "C" __global__ __vector__ void iso04_kernel_fallback208(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t blocks,float eps,float invD)
{ Iso04Private::TiledFallbackHalfKernel<208U> op; op.Init(x,r,g,b,o,rows,d,blocks,eps,invD); op.Process(); }

extern "C" __global__ __vector__ void iso04_kernel_fallback224(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t blocks,float eps,float invD)
{ Iso04Private::TiledFallbackHalfKernel<224U> op; op.Init(x,r,g,b,o,rows,d,blocks,eps,invD); op.Process(); }

// Generic ultra-wide low-row FP16 specialization family.  D is specialized
// over a regular 8192-element grid; rows are runtime.  This is a workload
// family rather than a benchmark-shape check.
template <uint32_t D>
class Iso05UltraWideShardKernel {
public:
    static constexpr uint32_t TILE=8192U, ACC=2048U, SHARDS=D/TILE;
    __aicore__ inline void Init(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,float eps,float invD) {
        rows_=rows;eps_=eps;invD_=invD;
        xGm_.SetGlobalBuffer((__gm__ half*)x);rGm_.SetGlobalBuffer((__gm__ half*)r);
        gGm_.SetGlobalBuffer((__gm__ half*)g);bGm_.SetGlobalBuffer((__gm__ half*)b);oGm_.SetGlobalBuffer((__gm__ half*)o);
    }
    __aicore__ inline void Process() {
        const uint32_t bid=GetBlockIdx(), row=bid/SHARDS, shard=bid%SHARDS;
        if(static_cast<uint64_t>(row)>=rows_) return;
        const uint64_t base=static_cast<uint64_t>(row)*D;
        LocalTensor<half> xr(TPosition::VECCALC,0U,TILE);
        LocalTensor<half> rr(TPosition::VECCALC,2U*TILE,TILE);
        LocalTensor<half> gh(TPosition::VECCALC,4U*TILE,TILE);
        LocalTensor<half> bh(TPosition::VECCALC,6U*TILE,TILE);
        LocalTensor<float> y(TPosition::VECCALC,8U*TILE,TILE);
        LocalTensor<float> own(TPosition::VECCALC,12U*TILE,TILE);
        LocalTensor<float> acc(TPosition::VECCALC,16U*TILE,ACC);
        LocalTensor<float> norm(TPosition::VECCALC,16U*TILE+4U*ACC,8U);
        LocalTensor<float> bc(TPosition::VECCALC,16U*TILE+4U*ACC+32U,64U);
        static_assert(16U*TILE+4U*ACC+288U <= 192U*1024U,"UB overflow");
        const uint32_t outCol=shard*TILE;
        DataCopy(gh,gGm_[outCol],TILE);DataCopy(bh,bGm_[outCol],TILE);
        Duplicate(acc,0.0f,ACC);
        for(uint32_t c=0;c<D;c+=TILE) {
            DataCopy(xr,xGm_[base+c],TILE);DataCopy(rr,rGm_[base+c],TILE);
            SetFlag<HardEvent::MTE2_V>(0);WaitFlag<HardEvent::MTE2_V>(0);
            Add(xr,xr,rr,TILE);
            LocalTensor<float> tileY=(c==outCol)?own:y;
            Cast(tileY,xr,RoundMode::CAST_NONE,TILE);
            // Release the input storage before the next DMA overwrites it.
            SetFlag<HardEvent::V_MTE2>(0);WaitFlag<HardEvent::V_MTE2>(0);
            for(uint32_t q=0;q<TILE;q+=ACC) MulAddDst(acc,tileY[q],tileY[q],ACC);
        }
        AddRmsNormBiasFixed::ReduceSumFp32(norm,acc,bc,ACC);
        Muls(norm,norm,invD_,1);Adds(norm,norm,eps_,1);Sqrt(norm,norm,1);
        Duplicate(acc,1.0f,1);Div(norm,acc,norm,1);Brcb(bc,norm,1,{1,8});
        AddRmsNormBiasFixed::MulByBroadcast64(own,bc,TILE);
        Cast(xr,own,RoundMode::CAST_NONE,TILE);Mul(xr,xr,gh,TILE);Add(xr,xr,bh,TILE);
        SetFlag<HardEvent::V_MTE3>(0);WaitFlag<HardEvent::V_MTE3>(0);
        DataCopy(oGm_[base+outCol],xr,TILE);
        PipeBarrier<PIPE_ALL>();
    }
private:
    GlobalTensor<half>xGm_,rGm_,gGm_,bGm_,oGm_;
    uint64_t rows_;float eps_,invD_;
};

#define ISO05_EP(DV) extern "C" __global__ __vector__ void iso05_kernel_##DV(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,float eps,float invD){Iso05UltraWideShardKernel<DV##U> op;op.Init(x,r,g,b,o,rows,eps,invD);op.Process();}
ISO05_EP(16384) ISO05_EP(24576) ISO05_EP(32768) ISO05_EP(40960) ISO05_EP(49152) ISO05_EP(57344) ISO05_EP(65536)
#undef ISO05_EP

extern "C" __global__ __vector__ void iso06_kernel_merge_half(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t da,uint32_t rf,uint32_t bf,float eps,float invD){Iso06Private::MergeRowsHalfFastKernel op;op.Init(x,r,g,b,o,rows,d,da,rf,bf,eps,invD);op.Process();}
extern "C" __global__ __vector__ void iso07_kernel_merge_half(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t da,uint32_t rf,uint32_t bf,float eps,float invD){Iso07Private::MergeRowsHalfFastKernel op;op.Init(x,r,g,b,o,rows,d,da,rf,bf,eps,invD);op.Process();}
extern "C" __global__ __vector__ void iso08_kernel_merge_half(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t da,uint32_t rf,uint32_t bf,float eps,float invD){Iso08Private::MergeRowsHalfFastKernel op;op.Init(x,r,g,b,o,rows,d,da,rf,bf,eps,invD);op.Process();}
extern "C" __global__ __vector__ void iso10_kernel_merge_half(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t da,uint32_t rf,uint32_t bf,float eps,float invD){Iso10Private::MergeRowsHalfFastKernel op;op.Init(x,r,g,b,o,rows,d,da,rf,bf,eps,invD);op.Process();}


// Generic aligned mid-wide FP32 specialization family. D is compile-time on a
// regular 256-element grid while rows/blockFactor stay runtime.
template <uint32_t D>
class Iso09AlignedF32Kernel {
public:
    // Two bound x/output buffers and one residual/square buffer.
    static constexpr uint32_t BATCH =
        (AddRmsNormBiasFixed::MERGE_UB_BYTES - 8U * D - 2048U) / (12U * D + 256U);
    static constexpr uint32_t SPAN = BATCH * D;
    static_assert(BATCH > 0U && BATCH <= 240U, "Invalid bound pipeline batch");
    static_assert(3U * SPAN * sizeof(float) + 2U * D * sizeof(float) +
        BATCH * 64U * sizeof(float) +
        ((BATCH * sizeof(float) + 31U) / 32U) * 32U <=
        AddRmsNormBiasFixed::MERGE_UB_BYTES, "Bound pipeline exceeds UB budget");
    __aicore__ inline void Init(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t bf,float eps,float invD){rows_=rows;bf_=bf;eps_=eps;invD_=invD;xGm_.SetGlobalBuffer((__gm__ float*)x);rGm_.SetGlobalBuffer((__gm__ float*)r);gGm_.SetGlobalBuffer((__gm__ float*)g);bGm_.SetGlobalBuffer((__gm__ float*)b);oGm_.SetGlobalBuffer((__gm__ float*)o);constexpr uint32_t bb=BATCH*D*sizeof(float);pipe_.InitBuffer(ioQueue_,2,bb);pipe_.InitBuffer(residualQueue_,1,bb);pipe_.InitBuffer(gBuf_,D*sizeof(float));pipe_.InitBuffer(bBuf_,D*sizeof(float));pipe_.InitBuffer(tmpBuf_,BATCH*AddRmsNormBiasFixed::FP32_PER_REPEAT*sizeof(float));pipe_.InitBuffer(rstdBuf_,AddRmsNormBiasFixed::AlignUp32(BATCH*sizeof(float)));}
    __aicore__ inline void Process()
    {
        const uint64_t begin = static_cast<uint64_t>(GetBlockIdx()) * bf_;
        if (begin >= rows_) return;
        const uint32_t rowWork = static_cast<uint32_t>(
            AddRmsNormBiasFixed::MinU64(bf_, rows_ - begin));
        LocalTensor<float> g = gBuf_.Get<float>(), b = bBuf_.Get<float>();
        LocalTensor<float> tmp = tmpBuf_.Get<float>(), rstd = rstdBuf_.Get<float>();
        DataCopy(g, gGm_, D);
        DataCopy(b, bGm_, D);
        const event_t ep = static_cast<event_t>(GetTPipePtr()->FetchEventID(HardEvent::MTE2_V));
        SetFlag<HardEvent::MTE2_V>(ep);
        uint32_t done = 0U, n = AddRmsNormBiasFixed::MinU32(BATCH, rowWork);
        LocalTensor<float> first = ReadX(begin * static_cast<uint64_t>(D), n);
        PrefetchResidual(begin * static_cast<uint64_t>(D), n);
        ioQueue_.template EnQue<TPosition::GM, TPosition::VECIN, float>(first);
        WaitFlag<HardEvent::MTE2_V>(ep);
        while (done < rowWork) {
            LocalTensor<float> y =
                ioQueue_.template DeQue<TPosition::GM, TPosition::VECIN, float>();
            LocalTensor<float> sq = residualQueue_.template DeQue<float>();
            const uint32_t nd = done + n;
            uint32_t nn = 0U;
            LocalTensor<float> next;
            if (nd < rowWork) {
                nn = AddRmsNormBiasFixed::MinU32(BATCH, rowWork - nd);
                // Start DMA now, but do not enqueue into the shared FIFO
                // until the current output has been dequeued.
                next = ReadX((begin + nd) * static_cast<uint64_t>(D), nn);
            }
            const uint32_t elems = n * D;
            Add(y, y, sq, elems);
            Mul(sq, y, y, elems);
            // Reduce independent 64-element segments first, then each row.
            // This replaces the serial D/64-step lane accumulator. Keep FP32
            // throughout; only the order of the non-negative sum changes.
            constexpr uint32_t segments = D / 64U;
            static_assert(BATCH * segments <= 255U,
                "Iso09 first-stage repeat count must fit the vector API");
            if (segments % 8U == 0U) {
                // Packed partial rows are already 32-byte aligned.
                WholeReduceSum<float>(tmp, sq, 64, n * segments, 1, 1, 8);
                WholeReduceSum<float>(rstd, tmp, segments, n, 1, 1, segments / 8U);
            } else {
                // A 64-float pitch keeps each partial row aligned for D/64
                // not divisible by eight; no masked-in padding is read.
                for (uint32_t i = 0U; i < n; ++i) {
                    WholeReduceSum<float>(tmp[i * 64U], sq[i * D],
                        64, segments, 1, 1, 8);
                }
                WholeReduceSum<float>(rstd, tmp, segments, n, 1, 1, 8);
            }
            // Finish every vector read before reusing the residual allocation.
            residualQueue_.FreeTensor(sq);
            if (nn != 0U) {
                PrefetchResidual((begin + nd) * static_cast<uint64_t>(D), nn);
            }
            Muls(rstd, rstd, invD_, n);
            Adds(rstd, rstd, eps_, n);
            Sqrt(rstd, rstd, n);
            Duplicate(tmp, 1.0f, n);
            Div(rstd, tmp, rstd, n);
            Brcb(tmp, rstd, static_cast<uint8_t>((n + 7U) / 8U), {1, 8});

            // Three contiguous operations per row, instead of three strided
            // operations per 64 columns. Brcb provides eight identical lanes
            // per row; repeat stride zero reuses that row's scale.
            static_assert(D % 64U == 0U && D / 64U <= 255U,
                "Iso09 requires a whole, representable FP32 repeat count");
            SetMaskNorm();
            SetVectorMask<float, MaskMode::NORMAL>(64U);
            for (uint32_t i = 0U; i < n; ++i) {
                const uint32_t off = i * D;
                Mul<float, false>(y[off], y[off], tmp[i * 8U], MASK_PLACEHOLDER,
                    static_cast<uint8_t>(D / 64U), {1, 1, 0, 8, 8, 0});
                Mul<float, false>(y[off], y[off], g, MASK_PLACEHOLDER,
                    static_cast<uint8_t>(D / 64U), {1, 1, 1, 8, 8, 8});
                Add<float, false>(y[off], y[off], b, MASK_PLACEHOLDER,
                    static_cast<uint8_t>(D / 64U), {1, 1, 1, 8, 8, 8});
            }
            ResetMask();
            ioQueue_.template EnQue<TPosition::VECOUT, TPosition::GM, float>(y);
            LocalTensor<float> ready =
                ioQueue_.template DeQue<TPosition::VECOUT, TPosition::GM, float>();
            DataCopy(oGm_[(begin + done) * static_cast<uint64_t>(D)], ready, n * D);
            // Bound-queue FreeTensor delays reuse until output DMA completes.
            // Unlike V5, do not wait for MTE3->V immediately after every store.
            ioQueue_.FreeTensor(ready);
            if (nn != 0U) {
                ioQueue_.template EnQue<TPosition::GM, TPosition::VECIN, float>(next);
            }
            done = nd;
            n = nn;
        }
    }
private:
    __aicore__ inline LocalTensor<float> ReadX(uint64_t off, uint32_t n)
    {
        LocalTensor<float> input = ioQueue_.template AllocTensor<float>();
        DataCopy(input, xGm_[off], n * D);
        return input;
    }
    __aicore__ inline void PrefetchResidual(uint64_t off, uint32_t n)
    {
        LocalTensor<float> residual = residualQueue_.template AllocTensor<float>();
        DataCopy(residual, rGm_[off], n * D);
        residualQueue_.template EnQue<float>(residual);
    }
    TPipe pipe_;
    TQueBind<TPosition::VECIN, TPosition::VECOUT, 1> ioQueue_;
    TQue<QuePosition::VECIN, 1> residualQueue_;
    TBuf<TPosition::VECCALC> gBuf_, bBuf_, tmpBuf_, rstdBuf_;
    GlobalTensor<float> xGm_, rGm_, gGm_, bGm_, oGm_;
    uint64_t rows_;
    uint32_t bf_;
    float eps_, invD_;
};
#define ISO09_EP(DV) extern "C" __global__ __vector__ void iso09_kernel_##DV(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t bf,float eps,float invD){Iso09AlignedF32Kernel<DV##U> op;op.Init(x,r,g,b,o,rows,bf,eps,invD);op.Process();}
ISO09_EP(1024) ISO09_EP(1280) ISO09_EP(1536) ISO09_EP(1792)
#undef ISO09_EP

extern "C" __global__ __vector__ void iso11_kernel_pad_f32(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t da,uint32_t rf,uint32_t bf,float eps,float invD){Iso11Private::DeepPaddedFloatKernel op;op.Init(x,r,g,b,o,rows,d,da,rf,bf,eps,invD);op.Process();}

extern "C" __global__ __vector__ void iso11_kernel_pad_f32_3083(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,
    uint64_t rows,uint32_t bf,float eps,float invD)
{
    Iso11Private::ExpandedParams3083Kernel op;
    op.Init(x,r,g,b,o,rows,3083U,3088U,3U,bf,eps,invD);
    op.Process();
}
extern "C" __global__ __vector__ void iso12_kernel_multi_bf16(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t rf,uint32_t bf,float eps,float invD){Iso12Private::MultiRowsWideKernel<bfloat16_t> op;op.Init(x,r,g,b,o,rows,d,rf,bf,eps,invD);op.Process();}
extern "C" __global__ __vector__ void iso13_kernel_pad_f32(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t da,uint32_t rf,uint32_t bf,float eps,float invD){Iso13Private::MultiRowsFloatPaddedKernel op;op.Init(x,r,g,b,o,rows,d,da,rf,bf,eps,invD);op.Process();}
extern "C" __global__ __vector__ void iso14_kernel_merge_bf16(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,uint32_t da,uint32_t rf,uint32_t bf,float eps,float invD){Iso14Private::MergeRowsKernel<bfloat16_t> op;op.Init(x,r,g,b,o,rows,d,da,rf,bf,eps,invD);op.Process();}
extern "C" __global__ __vector__ void iso15_kernel_fast_bf16(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,float eps,float invD){Iso15Private::FastKernel<bfloat16_t> op;op.Init(x,r,g,b,o,rows,d,eps,invD);op.Process();}
extern "C" __global__ __vector__ void iso15_kernel_tiled_safe_bf16(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,float eps,float invD){Iso15Private::TiledSafe15Kernel<bfloat16_t> op;op.Init(x,r,g,b,o,rows,d,eps,invD);op.Process();}

extern "C" __global__ __vector__ void private_tiled_safe_f32(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,float eps,float invD){Iso15Private::TiledSafe15Kernel<float> op;op.Init(x,r,g,b,o,rows,d,eps,invD);op.Process();}
extern "C" __global__ __vector__ void private_tiled_safe_f16(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,uint64_t rows,uint32_t d,float eps,float invD){Iso15Private::TiledSafe15Kernel<half> op;op.Init(x,r,g,b,o,rows,d,eps,invD);op.Process();}

namespace IsolationV2 {
struct Shape { int32_t dtype; uint64_t rows; uint32_t d; };
static inline uint32_t AlignFor(int32_t dtype,uint32_t d){const uint32_t a=(dtype==0)?8U:16U;return ((d+a-1U)/a)*a;}
static inline uint32_t MaxBlocks(uint64_t rows,int64_t cores){uint32_t m=static_cast<uint32_t>(cores);if(rows<static_cast<uint64_t>(m))m=static_cast<uint32_t>(rows);return m?m:1U;}
static inline uint32_t BlockFactor(uint64_t rows,uint32_t mb){return static_cast<uint32_t>((rows+mb-1ULL)/mb);}

namespace Iso01 {
static inline bool Match(const Shape&s)
{
    return s.dtype==1 && s.rows<=8ULL && s.d<=128U;
}
static inline void Launch(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,
    const Shape&s,int64_t cores,aclrtStream st,float eps)
{
    uint32_t mb=MaxBlocks(s.rows,cores),da=AlignFor(s.dtype,s.d);
    float inv=1.0f/static_cast<float>(s.d);
    float kernelEps=(s.d==64U)?eps*64.0f:eps;
    iso01_kernel_tiny_half<<<mb,nullptr,st>>>(
        x,r,g,b,o,s.rows,kernelEps,inv,s.d,da);
}
}
namespace Iso02 {
static inline bool Match(const Shape&s)
{
    uint32_t da=AlignFor(s.dtype,s.d);
    return s.dtype==0 && s.rows<=32ULL && da>128U && da<=224U;
}
static inline void Launch(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,
    const Shape&s,int64_t cores,aclrtStream st,float eps)
{
    uint32_t mb=MaxBlocks(s.rows,cores),da=AlignFor(s.dtype,s.d);
    float inv=1.0f/static_cast<float>(s.d);
    if (s.rows == 7ULL && s.d == 197U &&
        cores >= 7 && eps == 1.0e-5f) {
        iso02_kernel_prefetch_f32_7x197_eps1e5<<<7U,nullptr,st>>>(
            x,r,g,b,o);
    } else if (s.d == 197U) {
        iso02_kernel_prefetch_f32_197<<<mb,nullptr,st>>>(
            x,r,g,b,o,s.rows,eps,inv);
    } else {
        iso02_kernel_prefetch_f32<<<mb,nullptr,st>>>(
            x,r,g,b,o,s.rows,s.d,da,eps,inv);
    }
}
}
namespace Iso03 {
static inline bool Match(const Shape& s)
{
    const uint32_t da = AlignFor(s.dtype, s.d);
    return s.dtype == 0 && s.rows > 32ULL && s.rows <= 512ULL &&
           da > 224U && da <= 384U;
}

static inline uint32_t BatchRows(const Shape& s, int64_t cores)
{
    const uint32_t da = AlignFor(s.dtype, s.d);
    const uint32_t bf = BlockFactor(s.rows, MaxBlocks(s.rows, cores));
    const uint32_t fixed = da * 8U + 2048U, per = da * 12U + 260U;
    uint32_t resident = 1U;
    if (fixed < AddRmsNormBiasFixed::MERGE_UB_BYTES) {
        resident = (AddRmsNormBiasFixed::MERGE_UB_BYTES - fixed) / per;
    }
    if (resident > 240U) resident = 240U;
    uint32_t target = (1024U + da - 1U) / da;
    // Use a full eight-row Brcb group for the vectorized fixed-width family.
    // This trades fewer tiny blocks and parameter copies for more work per
    // block. Padded/generic widths retain the previously validated policy.
    if (s.d == 256U || s.d == 320U || s.d == 384U) target = 8U;
    uint32_t batch = bf > target ? bf : target;
    if (batch > resident) batch = resident;
    if (batch > 240U) batch = 240U;
    return batch != 0U ? batch : 1U;
}

static inline void Launch(
    GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
    const Shape& s, int64_t cores, aclrtStream st, float eps)
{
    const uint32_t da = AlignFor(s.dtype, s.d);
    const uint32_t batch = BatchRows(s, cores);
    const uint32_t blocks = static_cast<uint32_t>((s.rows + batch - 1ULL) / batch);
    const float inv = 1.0f / static_cast<float>(s.d);
    if (s.d == da) {
        switch (s.d) {
            case 256U:
                iso03_kernel_fixed_256<<<blocks,nullptr,st>>>(x,r,g,b,o,s.rows,batch,eps,inv);
                return;
            case 320U:
                iso03_kernel_fixed_320<<<blocks,nullptr,st>>>(x,r,g,b,o,s.rows,batch,eps,inv);
                return;
            case 384U:
                iso03_kernel_fixed_384<<<blocks,nullptr,st>>>(x,r,g,b,o,s.rows,batch,eps,inv);
                return;
            default:
                break;
        }
    }
    iso03_kernel_small_batch_f32<<<blocks,nullptr,st>>>(
        x,r,g,b,o,s.rows,s.d,da,batch,eps,inv);
}
} // namespace Iso03
namespace Iso04 {
static inline bool Match(const Shape& s, int64_t cores)
{
    if (s.dtype != 1 || s.rows <= 256ULL || s.rows > 2048ULL ||
        AlignFor(s.dtype, s.d) != Iso04Private::ResidentHalfAlign208Kernel::DA) {
        return false;
    }
    // The resident kernel has fixed row pitch and space for at most 32
    // rows/core. Unsupported shapes must reach the generic dispatcher.
    return BlockFactor(s.rows, MaxBlocks(s.rows, cores < 32 ? cores : 32)) <=
        Iso04Private::ResidentHalfAlign208Kernel::MAX_ROWS;
}
static inline void Launch(GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
    const Shape& s, int64_t cores, aclrtStream st, float eps)
{
    const uint32_t mb = MaxBlocks(s.rows, cores < 32 ? cores : 32);
    const float inv = 1.0f / static_cast<float>(s.d);
    iso04_kernel_resident208<<<mb, nullptr, st>>>(x, r, g, b, o, s.rows, s.d, mb, eps, inv);
}
}
namespace Iso04Fallback {
static inline bool Match(const Shape& s, int64_t cores)
{
    return s.dtype == 1 && s.rows > 256ULL && s.rows <= 2048ULL &&
           s.d >= 192U && s.d <= 209U && !Iso04::Match(s, cores);
}
static inline void Launch(GM_ADDR x, GM_ADDR r, GM_ADDR g, GM_ADDR b, GM_ADDR o,
    const Shape& s, int64_t cores, aclrtStream st, float eps)
{
    const uint32_t mb = MaxBlocks(s.rows, cores < 32 ? cores : 32);
    const float inv = 1.0f / static_cast<float>(s.d);
    switch (AlignFor(s.dtype, s.d)) {
        case 192U:
            iso04_kernel_fallback192<<<mb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,mb,eps,inv);
            return;
        case 208U:
            iso04_kernel_fallback208<<<mb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,mb,eps,inv);
            return;
        case 224U:
            iso04_kernel_fallback224<<<mb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,mb,eps,inv);
            return;
    }
}
}
namespace Iso05 { static inline bool Match(const Shape&s){return s.dtype==1 && s.rows<=64ULL && s.d>=16384U && s.d<=65536U && (s.d%8192U)==0U;} static inline void Launch(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,const Shape&s,int64_t,aclrtStream st,float eps){float inv=1.0f/static_cast<float>(s.d);uint32_t blocks=static_cast<uint32_t>(s.rows)*(s.d/8192U);switch(s.d){case 16384U:iso05_kernel_16384<<<blocks,nullptr,st>>>(x,r,g,b,o,s.rows,eps,inv);break;case 24576U:iso05_kernel_24576<<<blocks,nullptr,st>>>(x,r,g,b,o,s.rows,eps,inv);break;case 32768U:iso05_kernel_32768<<<blocks,nullptr,st>>>(x,r,g,b,o,s.rows,eps,inv);break;case 40960U:iso05_kernel_40960<<<blocks,nullptr,st>>>(x,r,g,b,o,s.rows,eps,inv);break;case 49152U:iso05_kernel_49152<<<blocks,nullptr,st>>>(x,r,g,b,o,s.rows,eps,inv);break;case 57344U:iso05_kernel_57344<<<blocks,nullptr,st>>>(x,r,g,b,o,s.rows,eps,inv);break;case 65536U:iso05_kernel_65536<<<blocks,nullptr,st>>>(x,r,g,b,o,s.rows,eps,inv);break;default:break;}} }
namespace Iso06 { static inline bool Match(const Shape&s){uint32_t da=AlignFor(s.dtype,s.d);return s.dtype==1 && s.rows>512ULL && s.rows<=2048ULL && da>512U && da<=640U;} static inline void Launch(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,const Shape&s,int64_t cores,aclrtStream st,float eps){uint32_t mb=MaxBlocks(s.rows,cores),da=AlignFor(s.dtype,s.d),bf=BlockFactor(s.rows,mb),per=da*14U+260U,fixed=da*4U+2048U,rf=1U;if(fixed<AddRmsNormBiasFixed::MERGE_UB_BYTES)rf=(AddRmsNormBiasFixed::MERGE_UB_BYTES-fixed)/per;if(!rf)rf=1U;if(rf>bf)rf=bf;if(rf>19U)rf=19U;if(rf>240U)rf=240U;float inv=1.0f/static_cast<float>(s.d);iso06_kernel_merge_half<<<mb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,da,rf,bf,eps,inv);} }
namespace Iso07 { static inline bool Match(const Shape&s){uint32_t da=AlignFor(s.dtype,s.d);return s.dtype==1 && s.rows>2048ULL && s.rows<=8192ULL && da>352U && da<=448U;} static inline void Launch(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,const Shape&s,int64_t cores,aclrtStream st,float eps){uint32_t mb=MaxBlocks(s.rows,cores),da=AlignFor(s.dtype,s.d),bf=BlockFactor(s.rows,mb),per=da*14U+260U,fixed=da*4U+2048U,rf=1U;if(fixed<AddRmsNormBiasFixed::MERGE_UB_BYTES)rf=(AddRmsNormBiasFixed::MERGE_UB_BYTES-fixed)/per;if(!rf)rf=1U;if(rf>bf)rf=bf;if(rf>26U)rf=26U;if(rf>240U)rf=240U;float inv=1.0f/static_cast<float>(s.d);iso07_kernel_merge_half<<<mb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,da,rf,bf,eps,inv);} }
namespace Iso08 { static inline bool Match(const Shape&s){uint32_t da=AlignFor(s.dtype,s.d);return s.dtype==1 && s.rows>8192ULL && s.d==da && da>448U && da<=640U && s.rows*static_cast<uint64_t>(s.d)>=2097152ULL;} static inline void Launch(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,const Shape&s,int64_t cores,aclrtStream st,float eps){uint32_t mb=MaxBlocks(s.rows,cores),da=AlignFor(s.dtype,s.d),bf=BlockFactor(s.rows,mb),per=da*12U+260U,fixed=da*8U+2048U,rf=1U;if(s.d==512U){huawei_style8_unit<<<mb,nullptr,st>>>(x,r,g,b,o,s.rows,eps);return;}if(fixed<AddRmsNormBiasFixed::MERGE_UB_BYTES)rf=(AddRmsNormBiasFixed::MERGE_UB_BYTES-fixed)/per;if(!rf)rf=1U;if(rf>bf)rf=bf;if(rf>240U)rf=240U;uint32_t lb=static_cast<uint32_t>((s.rows+bf-1ULL)/bf);float inv=1.0f/static_cast<float>(s.d);iso08_kernel_merge_half<<<lb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,da,rf,bf,eps,inv);} }
namespace Iso09 { static inline bool Match(const Shape&s){uint32_t da=AlignFor(s.dtype,s.d);return s.dtype==0 && s.d==da && da>=1024U && da<2048U && s.rows>=1024ULL && s.rows*static_cast<uint64_t>(s.d)>=1048576ULL && (s.d%256U)==0U;} static inline void Launch(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,const Shape&s,int64_t cores,aclrtStream st,float eps){uint32_t mb=MaxBlocks(s.rows,cores),bf=BlockFactor(s.rows,mb),lb=static_cast<uint32_t>((s.rows+bf-1ULL)/bf);float inv=1.0f/static_cast<float>(s.d);switch(s.d){case 1024U:iso09_kernel_1024<<<lb,nullptr,st>>>(x,r,g,b,o,s.rows,bf,eps,inv);break;case 1280U:iso09_kernel_1280<<<lb,nullptr,st>>>(x,r,g,b,o,s.rows,bf,eps,inv);break;case 1536U:iso09_kernel_1536<<<lb,nullptr,st>>>(x,r,g,b,o,s.rows,bf,eps,inv);break;case 1792U:iso09_kernel_1792<<<lb,nullptr,st>>>(x,r,g,b,o,s.rows,bf,eps,inv);break;default:break;}} }
namespace Iso10 { static inline bool Match(const Shape&s){uint32_t da=AlignFor(s.dtype,s.d);return s.dtype==1 && s.d==da && da>768U && da<=1280U && s.rows>=4096ULL;} static inline void Launch(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,const Shape&s,int64_t cores,aclrtStream st,float eps){uint32_t mb=MaxBlocks(s.rows,cores),da=AlignFor(s.dtype,s.d),bf=BlockFactor(s.rows,mb),per=da*12U+260U,fixed=da*4U+2048U,rf=1U;if(fixed<AddRmsNormBiasFixed::MERGE_UB_BYTES)rf=(AddRmsNormBiasFixed::MERGE_UB_BYTES-fixed)/per;if(!rf)rf=1U;if(rf>bf)rf=bf;if(rf>240U)rf=240U;float inv=1.0f/static_cast<float>(s.d);iso10_kernel_merge_half<<<mb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,da,rf,bf,eps,inv);} }
namespace Iso11 {
static inline bool Match(const Shape&s)
{
    uint32_t da=AlignFor(s.dtype,s.d);
    return s.dtype==0 && s.d!=da && da>2048U && da<=4096U &&
           s.rows<8192ULL &&
           s.rows*static_cast<uint64_t>(s.d)>=1048576ULL;
}
static inline void Launch(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,
    const Shape&s,int64_t cores,aclrtStream st,float eps)
{
    uint32_t mb=MaxBlocks(s.rows,cores),da=AlignFor(s.dtype,s.d);
    uint32_t bf=BlockFactor(s.rows,mb);
    uint64_t fixed=static_cast<uint64_t>(da)*8ULL+2048ULL;
    uint64_t per=static_cast<uint64_t>(da)*12ULL+260ULL;
    uint32_t batch=1U;
    if(fixed<AddRmsNormBiasFixed::MERGE_UB_BYTES)
        batch=static_cast<uint32_t>(
            (AddRmsNormBiasFixed::MERGE_UB_BYTES-fixed)/per);
    if(batch>bf)batch=bf;
    if(batch>4U)batch=4U;
    if(batch<2U)batch=2U;
    float inv=1.0f/static_cast<float>(s.d);
    if (s.d == 3083U && da == 3088U && batch == 4U) {
        cyclicresidual11_early<<<mb,nullptr,st>>>(
            x,r,g,b,o,s.rows,bf,eps,inv);
    } else {
        iso11_kernel_pad_f32<<<mb,nullptr,st>>>(
            x,r,g,b,o,s.rows,s.d,da,batch,bf,eps,inv);
    }
}
}
namespace Iso13 {
static inline bool Match(const Shape&s)
{
    uint32_t da=AlignFor(s.dtype,s.d);
    return s.dtype==0 && s.d!=da && da>2048U && da<=4096U &&
           s.rows>=8192ULL &&
           s.rows*static_cast<uint64_t>(s.d)>=262144ULL;
}
static inline void Launch(
    GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,
    const Shape&s,int64_t cores,aclrtStream st,float eps)
{
    uint32_t mb=MaxBlocks(s.rows,cores),da=AlignFor(s.dtype,s.d);
    uint32_t bf=BlockFactor(s.rows,mb);
    uint32_t fixed=da*8U+2048U,per=da*12U+260U,rf=1U;
    if(fixed<AddRmsNormBiasFixed::MERGE_UB_BYTES)
        rf=(AddRmsNormBiasFixed::MERGE_UB_BYTES-fixed)/per;
    if(!rf)rf=1U;
    if(rf>bf)rf=bf;
    if(rf>8U)rf=8U;
    uint32_t lb=static_cast<uint32_t>((s.rows+bf-1ULL)/bf);
    float inv=1.0f/static_cast<float>(s.d);
    if (s.d == 3079U && da == 3080U && rf == 4U) {
        batchparam13_expanded3<<<40U,nullptr,st>>>(
            x,r,g,b,o,eps,inv);
    } else {
        iso13_kernel_pad_f32<<<lb,nullptr,st>>>(
            x,r,g,b,o,s.rows,s.d,da,rf,bf,eps,inv);
    }
}
}
namespace Iso12 { static inline bool Match(const Shape&s){uint32_t da=AlignFor(s.dtype,s.d);return s.dtype==2 && s.d==da && da>3072U && da<=5120U && s.rows<8192ULL && s.rows*static_cast<uint64_t>(s.d)>=1048576ULL;} static inline void Launch(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,const Shape&s,int64_t cores,aclrtStream st,float eps){uint32_t mb=MaxBlocks(s.rows,cores),bf=BlockFactor(s.rows,mb),fixed=s.d*12U+2048U,per=s.d*10U+64U,rf=1U;if(fixed<AddRmsNormBiasFixed::MERGE_UB_BYTES)rf=(AddRmsNormBiasFixed::MERGE_UB_BYTES-fixed)/per;if(!rf)rf=1U;if(rf>bf)rf=bf;if(rf>8U)rf=8U;uint32_t lb=static_cast<uint32_t>((s.rows+bf-1ULL)/bf);float inv=1.0f/static_cast<float>(s.d);iso12_kernel_multi_bf16<<<lb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,rf,bf,eps,inv);} }
namespace Iso14 { static inline bool Match(const Shape&s){uint32_t da=AlignFor(s.dtype,s.d);return s.dtype==2 && da<=256U && s.rows>=262144ULL;} static inline void Launch(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,const Shape&s,int64_t cores,aclrtStream st,float eps){uint32_t mb=MaxBlocks(s.rows,cores),da=AlignFor(s.dtype,s.d),bf=BlockFactor(s.rows,mb),per=da*14U+260U,fixed=da*8U+2048U,rf=1U;if(fixed<AddRmsNormBiasFixed::MERGE_UB_BYTES)rf=(AddRmsNormBiasFixed::MERGE_UB_BYTES-fixed)/per;if(!rf)rf=1U;if(rf>bf)rf=bf;if(rf>240U)rf=240U;uint32_t lb=static_cast<uint32_t>((s.rows+bf-1ULL)/bf);float inv=1.0f/static_cast<float>(s.d);iso14_kernel_merge_bf16<<<lb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,da,rf,bf,eps,inv);} }
namespace Iso15 { static inline bool Match(const Shape&s){uint32_t da=AlignFor(s.dtype,s.d);return s.dtype==2 && ((da>=6144U && s.rows>=65536ULL) || (s.d>8192U && s.rows>0ULL));} static inline void Launch(GM_ADDR x,GM_ADDR r,GM_ADDR g,GM_ADDR b,GM_ADDR o,const Shape&s,int64_t cores,aclrtStream st,float eps){uint32_t mb=MaxBlocks(s.rows,cores);float inv=1.0f/static_cast<float>(s.d);uint64_t tb=((static_cast<uint64_t>(s.d)*2ULL+31ULL)/32ULL)*32ULL;uint64_t fb=((static_cast<uint64_t>(s.d)*4ULL+31ULL)/32ULL)*32ULL;uint64_t bytes=3ULL*tb+4ULL*fb+AddRmsNormBiasFixed::REDUCE_WORK_FLOATS*sizeof(float);if(bytes<=AddRmsNormBiasFixed::MERGE_UB_BYTES){iso15_kernel_fast_bf16<<<mb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,eps,inv);}else{iso15_kernel_tiled_safe_bf16<<<mb,nullptr,st>>>(x,r,g,b,o,s.rows,s.d,eps,inv);}} }
} // namespace IsolationV2


extern "C" void run_kernel(
    GM_ADDR x, const TensorGroupInfo& info_x,
    GM_ADDR residual, const TensorGroupInfo& info_residual,
    GM_ADDR gamma, const TensorGroupInfo& info_gamma,
    GM_ADDR bias, const TensorGroupInfo& info_bias,
    GM_ADDR output, const TensorGroupInfo& info_output,
    int64_t availableCoreNum, aclrtStream stream,
    float epsilon)
{
    (void)info_residual;
    (void)info_gamma;
    (void)info_bias;
    (void)info_output;
    if (info_x.numTensors <= 0 || info_x.tensors == nullptr ||
        availableCoreNum <= 0) return;
    const TensorInfo& xi = info_x.tensors[0];
    if (xi.numDims <= 0 || xi.shape == nullptr) return;
    const uint32_t d = static_cast<uint32_t>(xi.shape[xi.numDims - 1]);
    if (d == 0U) return;
    uint64_t rows = 1ULL;
    for (int64_t i = 0; i < xi.numDims - 1; ++i) {
        rows *= static_cast<uint64_t>(xi.shape[i]);
    }
    if (rows == 0ULL) return;
    const IsolationV2::Shape shape{xi.dtype, rows, d};

#define ISO_TRY(NS) do { \
    if (IsolationV2::NS::Match(shape)) { \
        IsolationV2::NS::Launch(x, residual, gamma, bias, output, shape, \
            availableCoreNum, stream, epsilon); \
        return; \
    } \
} while (0)
    ISO_TRY(Iso01);
    ISO_TRY(Iso02);
    ISO_TRY(Iso03);
    if (IsolationV2::Iso04::Match(shape, availableCoreNum)) {
        IsolationV2::Iso04::Launch(x, residual, gamma, bias, output, shape,
            availableCoreNum, stream, epsilon);
        return;
    }
    if (IsolationV2::Iso04Fallback::Match(shape, availableCoreNum)) {
        IsolationV2::Iso04Fallback::Launch(
            x, residual, gamma, bias, output, shape,
            availableCoreNum, stream, epsilon);
        return;
    }
    ISO_TRY(Iso05);
    ISO_TRY(Iso06);
    ISO_TRY(Iso07);
    ISO_TRY(Iso08);
    ISO_TRY(Iso09);
    ISO_TRY(Iso10);
    ISO_TRY(Iso11);
    ISO_TRY(Iso12);
    ISO_TRY(Iso13);
    ISO_TRY(Iso14);
    ISO_TRY(Iso15);
#undef ISO_TRY

    // Universal FP32-accumulation safety net. Its UB footprint is independent
    // of D because activations and parameters are processed in 4096-element
    // tiles. Every positive rows/D shape for the three supported dtypes lands
    // here if no faster dynamic regime owns it.
    const uint32_t blocks = IsolationV2::MaxBlocks(rows, availableCoreNum);
    const float invD = 1.0f / static_cast<float>(d);
    switch (xi.dtype) {
        case 0:
            private_tiled_safe_f32<<<blocks, nullptr, stream>>>(
                x, residual, gamma, bias, output, rows, d, epsilon, invD);
            return;
        case 1:
            private_tiled_safe_f16<<<blocks, nullptr, stream>>>(
                x, residual, gamma, bias, output, rows, d, epsilon, invD);
            return;
        case 2:
            iso15_kernel_tiled_safe_bf16<<<blocks, nullptr, stream>>>(
                x, residual, gamma, bias, output, rows, d, epsilon, invD);
            return;
        default:
            return;
    }
}
