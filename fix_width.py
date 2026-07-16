import re
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

pages_dir = r'D:\0QuantSeed\src\pages'
for fname in os.listdir(pages_dir):
    if fname.startswith('4_') and fname.endswith('.py'):
        fpath = os.path.join(pages_dir, fname)
        print(f'Processing: {fpath}')
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace st.button(...width="stretch"...)
        content = re.sub(
            r'(st\.button\([^)]*?)width="stretch"\s*,\s*',
            r'\1use_container_width=True, ',
            content
        )
        content = re.sub(
            r'(st\.button\([^)]*?)width="stretch"\s*\)',
            r'\1use_container_width=True)',
            content
        )

        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print('  Done')
