poly1 = dict()
poly2 = dict()

pl1 = list(map(float, input().split()))
pl2 = list(map(float, input().split()))

for i in range(int(pl1[0])):
    poly1[pl1[2 * i + 1]] = pl1[2 * i + 2]


for i in range(int(pl2[0])):
    poly1[pl2[2 * i + 1]] = poly1.get(pl2[2 * i + 1], 0.0) + pl2[2 * i + 2]

poly1 = {exp: coeff for exp, coeff in poly1.items() if abs(coeff) > 1e-6}
sorted_items = sorted(poly1.items(), key=lambda x: x[0], reverse=True)

if not sorted_items:
    print("0")
else:
    print(len(poly1), end="")
    for key, val in sorted_items:
        print(f" {int(key)} {val:.1f}", end="")
