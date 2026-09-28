import argparse
import gzip
from pathlib import Path

parser = argparse.ArgumentParser(description="Uncompress a trusted locally generated sample for JSON import")
parser.add_argument("source", type=Path)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
args.destination.write_bytes(gzip.decompress(args.source.read_bytes()))
print(args.destination)
