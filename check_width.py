import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

dirs = [r'D:\0QuantSeed\src', r'D:\0QuantSeed\src\pages']
for d in dirs:
    for f in os.listdir(d):
        if f.endswith('.py'):
            fpath = os.path.join(d, f)
            with open(fpath, encoding='utf-8') as fh:
                lines = fh.readlines()
            for i, line in enumerate(lines, 1):
                if 'width="stretch"' in line:
                    stripped = line.strip()
                    # Only flag if it's in st.button()
                    if 'st.button' in stripped:
                        print(f'BUG in {f} L{i}: {stripped[:100]}')
print('Check done')
