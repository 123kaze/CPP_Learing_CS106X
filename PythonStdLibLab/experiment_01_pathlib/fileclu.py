import argparse
import shutil
from pathlib import Path
from collections import defaultdict
from typing import Optional


def scan_directory(root: Path, extensions: Optional[list[str]] = None):
    """
    递归扫描目录，统计每种后缀的文件。

    返回:
      dict: {后缀: [Path列表]}
    """
    counts = defaultdict(list)
    for f in root.rglob("*"):
        if f.is_file():
            ext = f.suffix or "(无后缀)"
            if extensions and ext not in extensions:
                continue
            counts[ext].append(f)

    return counts

def print_stats(by_ext: dict[str,list[Path]]) -> None:
    '''

    :param by_ext:
    :return:
    '''
    print(f"\n{'后缀':<15} {'数量':<8} {'总大小':<12}")
    print("-" * 40)

    total_files = 0
    total_size = 0

    for ext in sorted(by_ext.keys()):
        files = by_ext[ext]
        size = sum(file.stat().st_size for file in files)
        print(f"{ext:<15} {len(files):<8} {format_size(size):<12}")
        total_files += len(files)
        total_size += size

    print("-" * 40)
    print(f"{'总计':<15} {total_files:<8} {format_size(total_size):<12}")

    all_files = [f for files in by_ext.values() for f in files]
    all_files.sort(key=lambda f: f.stat().st_size, reverse=True)
    if all_files:
        print(f"\n最大的 5 个文件:")
        for f in all_files[:5]:
            print(f"  {format_size(f.stat().st_size):>10s}  {f}")


def classify_copy(by_ext: dict, dest: Path, *, move: bool = False):
    """
    按后缀分类，复制或移动文件到目标目录。
    目标目录结构：dest/{ext_name}/file
    """
    for ext, files in by_ext.items():
        dir_name = ext.lstrip(".") if ext != '(无后缀)' else ext
        target_dir = dest / dir_name
        target_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            target = target_dir / f.name
            if move:
                print(f"移动: {f} -> {target}")
                shutil.move(str(f),str(target))
            else:
                print(f"复制: {f} -> {target}")
                shutil.copy2(str(f),str(target))


def format_size(size_bytes:float) -> str:
    for unit in ("B","KB","MB","GB"):
        if size_bytes < 1024:
            return f'{size_bytes:.1f} {unit}'
        size_bytes/=1024
    
    return f'{size_bytes:.1f} TB'

def main():
    parse = argparse.ArgumentParser(description="文件分类器")
    parse.add_argument("folder",type = str,help="要扫描的文件路径")
    parse.add_argument(
        "--copy-to",type=str,default=None,help="按后缀分类复制到目标目录"
    )
    parse.add_argument(
        "--move-to",default=None,help="按后缀分类移动到目标目录"
    )

    parse.add_argument(
        "--ext",nargs="*",default=None,
        help="只统计指定后缀(如 --ext .py .cpp)"
    )

    args = parse.parse_args()
    root = Path(args.folder)

    if not root.exists():
        print(f"Error: 不存在 —— {root}")
        return
    
    if not root.is_dir():
        print("Error: 不是目录 —— {root}")
        return
    
    extensions = None
    if args.ext:
        extensions = [e if e.startwith(".") else f".{e}" for e in args.ext]
        extensions = [e.lower() for e in extensions]
    
    print(f"扫描目录: {root}")
    by_ext = scan_directory(root,extensions)
    print_stats(by_ext)

    if args.copy_to:
        dest = Path(args.copy_to)
        classify_copy(by_ext,dest,move=False)
        print(f"\n分类复制完成: {dest}")
    
    if args.move_to:
        dest = Path(args.copy_to)
        classify_copy(by_ext,dest,move=True)
        print(f"\n分类移动完成: {dest}")
    
if __name__ == "__main__":
    main()