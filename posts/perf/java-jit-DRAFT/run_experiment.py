import subprocess
from tqdm import tqdm
import pandas as pd

results = []
tries = 200
rounds_defs = [
        1000000,
        5000000,
        10000000,
        50000000,
        100000000,
        500000000,
        1000000000
        ]

T = tqdm(total = len(rounds_defs) * 3 * tries)
for t in range(tries):
    for name, cmd in (
            ("c O0", ["./primesO0"]),
            ("c O3", ["./primesO3"]),
            ("java", ["java", "Primes"])
            ):
        for rounds in rounds_defs:
            out = subprocess.check_output(cmd + [str(rounds)])
            elapsed = int(out.split(b"Took ")[1].split(b" ", 1)[0])

            results.append((name, rounds, elapsed))
            T.update()

df = pd.DataFrame(results, columns=("prog", "rounds", "elapsed"))
df.to_parquet("results.parquet")
