#!/bin/bash
# Build the SkiQF driver on arm64 (clang). Headers: overlay/include (stub test_driver.h + links), variants/ unmodified.
set -e
cd "$(dirname "$0")"
O=../repos/saltsystemslab__SkiRentalAdaptiveQF
INC="-Ioverlay -Ioverlay/include -I$O -DSKIP_BOOL_DEF -D_GNU_SOURCE"
mkdir -p obj
for f in port/gqf.c port/partitioned_counter.c $O/src/hashutil.c $O/src/ll_table.c; do
  clang -std=gnu11 -O3 -DNDEBUG $INC -Wno-int-conversion -Wno-incompatible-function-pointer-types -w -c $f -o obj/$(basename $f .c).o
done
clang++ -std=c++17 -O3 -DNDEBUG $INC -w skiqf_orig_driver.cpp obj/*.o -o skiqf_orig_driver
