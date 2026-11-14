"""Write data_manifest_dani.tsv (relative path, size in bytes) for everything under data/, skipping READMEs and .part files."""
import pathlib, sys
root = pathlib.Path("data")
out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data_manifest_dani.tsv")
rows = sorted((p.relative_to(root).as_posix(), p.stat().st_size) for p in root.rglob("*")
              if p.is_file() and p.name != "README.md" and not p.name.endswith(".part") and not p.name.startswith("."))
out.write_text("path\tsize_bytes\n" + "".join(f"{a}\t{b}\n" for a, b in rows))
print(len(rows), "files ->", out)
