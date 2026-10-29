#!/bin/bash
# Build the official AdaptiveQF driver on arm64 (clang). port/ holds the patched core sources.
set -e
cd "$(dirname "$0")"
O=../repos/splatlab__adaptiveqf
INC="-I$O/include -I$O/reverse_maps/ll_table -I$O/reverse_maps/localmap -I$O/reverse_maps/mock -I$O -DSKIP_BOOL_DEF -D_GNU_SOURCE"
mkdir -p obj
for f in port/aqf.c port/gqf.c port/partitioned_counter.c $O/src/hashutil.c $O/reverse_maps/ll_table/ll_table.c; do
  clang -std=gnu11 -O3 -DNDEBUG $INC -Wno-int-conversion -Wno-incompatible-function-pointer-types -w -c $f -o obj/$(basename $f .c).o
done
clang++ -std=c++17 -O3 -DNDEBUG $INC -w aqf_orig_driver.cpp obj/*.o -o aqf_orig_driver
