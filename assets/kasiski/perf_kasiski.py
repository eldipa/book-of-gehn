import timeit
from cryptonita.stats.kasiski import as_ngram_repeated_positions, merge_overlaping, kasiski_test
from cryptonita import B

import math

import plotting
import seaborn as sns
import matplotlib.pyplot as plt

def perf__as_ngram_repeated_positions(number, repeat):
    s = B(open('test/ds/gpl_license', 'rb').read())

    num_steps = 8

    total_sz = len(s)
    step_sz = total_sz // num_steps

    env = globals().copy()
    y = []
    for i in range(num_steps):
        l = (i+1)*step_sz

        sub_s = s[:l]
        cmd = 'as_ngram_repeated_positions(sub_s, n=3)'

        env.update(locals())
        t = min(timeit.repeat(cmd, globals=env, number=number, repeat=repeat))
        print("Length", l, t)

        y.append(t)

    y = [t/y[0] for t in y]
    x = list(range(1, num_steps+1))
    sns.scatterplot(x, y, s=30)

    plt.plot([], [])

    x2 = list(x)
    x2.insert(0, 0)
    x2.append(num_steps+1)
    m = y[1] - y[0]
    y2 = [m*i for i in x2]
    plt.plot(x2, y2, linestyle='--')


def perf__merge_overlaping(number, repeat):
    s = B(open('test/ds/gpl_license', 'rb').read())
    l3_positions = as_ngram_repeated_positions(s, n=3)

    num_steps = 8

    total_sz = len(l3_positions)
    step_sz = total_sz // num_steps

    env = globals().copy()
    y = []
    for i in range(num_steps):
        l = (i+1)*step_sz
        pos_sorted = l3_positions[:l]
        cmd = 'merge_overlaping(pos_sorted)'

        env.update(locals())
        t = min(timeit.repeat(cmd, globals=env, number=number, repeat=repeat))
        print("Length", l, t)

        y.append(t)

    y = [t/y[0] for t in y]
    x = list(range(1, num_steps+1))
    sns.scatterplot(x, y, s=30)

    plt.plot([], [])

    x2 = list(x)
    x2.insert(0, 0)
    x2.append(num_steps+1)
    m = y[1] - y[0]
    y2 = [m*i for i in x2]
    plt.plot(x2, y2, linestyle='--')

def perf__kasiski_test(number, repeat):
    s = B(open('test/ds/gpl_license', 'rb').read())

    num_steps = 8

    total_sz = len(s)
    step_sz = total_sz // num_steps

    env = globals().copy()
    y = []
    for i in range(num_steps):
        l = (i+1)*step_sz
        sub_s = s[:l]
        cmd = 'kasiski_test(sub_s)'

        env.update(locals())
        t = min(timeit.repeat(cmd, globals=env, number=number, repeat=repeat))
        print("Length", l, t)

        y.append(t)

    y = [t/y[0] for t in y]
    x = list(range(1, num_steps+1))
    sns.scatterplot(x, y, s=30)

    # trick to make matplotlib to use the 'next' color in its color
    # pallete as 'scatterplot' resets the cycle.
    plt.plot([], [])

    x2 = list(x)
    x2.insert(0, 0)
    x2.append(num_steps+1)
    m = y[1] - y[0]
    y2 = [m*i for i in x2]
    plt.plot(x2, y2, linestyle='--')

    y2 = [0] + [i*math.log2(i) + y[0] for i in x2[1:]]
    plt.plot(x2, y2, linestyle='--')

with plotting.show("as_ngram_repeated_positions.png"):
    perf__as_ngram_repeated_positions(number=1, repeat=20)

with plotting.show("merge_overlaping.png"):
    perf__merge_overlaping(number=10, repeat=20)

with plotting.show("kasiski_test.png"):
    perf__kasiski_test(number=1, repeat=20)
