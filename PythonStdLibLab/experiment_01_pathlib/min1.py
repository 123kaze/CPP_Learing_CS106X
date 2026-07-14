# from pathlib import Path
#
# # 统计当前目录下各类文件的数量
# counts = {}
# for f in Path(".").iterdir():
#     if f.is_file():
#         ext = f.suffix or "(无后缀)"
#         counts[ext] = counts.get(ext, 0) + 1
#
# for ext, count in sorted(counts.items()):
#     print(f"{ext:10s}: {count} 个")


from pathlib import Path

counts = {}
names = []
for f in Path("..").glob("**/*"):
    if f.is_file():
        ext = f.suffix.lower() or "None"
        name = f.stem.lower()
        counts[ext] = counts.get(ext, 0) + 1
        names.append(name)

for ext, count in sorted(counts.items()):
    print(f"{ext:<10s}: {count} 个")

print('=================')
for name in names:
    print(f"{name}")