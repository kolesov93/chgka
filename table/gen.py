#!/usr/bin/env python3

if 1 == 2:
    cnt = 0
    for a in range(7):
        for b in range(7):
            if a == 6 and b == 6:
                continue
            cnt += 1
            print('qpdf --pages whole.pdf {} -- --empty {}{}.pdf'.format(cnt, a, b))
            if a == 5 and (b >= 1 and b <= 5):
                cnt += 1


cnt = -1
for a in range(7):
    for b in range(7):
        if a == 6 and b == 6:
            continue
        cnt += 1
        print('convert -density 150 whole.pdf[{}] -quality 90 {}{}.png'.format(cnt, a, b))
        if a == 5 and (b >= 1 and b <= 5):
            cnt += 1
