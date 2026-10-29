"""Reassemble the two unchanged transport parts after checking their SHA-256."""
from pathlib import Path
import hashlib
import sys

NAME = 'R7_NATIVE_FINITE_ORIGINAL_REPORTS_AND_BINDINGS_V1.zip'
PARTS = (
    (NAME + '.part-000', 8257536, '4fb238366c2b328bb3de4ba377744390d6801aa2f4281820c457151d42deaebe'),
    (NAME + '.part-001', 8210467, '0b4577b14c27d8ab168a663e16c26cbdd767e45e0829a1740cb63b3a1fca8f18'),
)
EXPECTED = 'b5a51bb87abc2d84be10bd24b0f7a1a8f20aa23bcc84666ecc9c9aeeaf97d6e7'

def main():
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    data = []
    for name, size, expected in PARTS:
        part = (directory / name).read_bytes()
        if len(part) != size or hashlib.sha256(part).hexdigest() != expected:
            raise ValueError('Original transport-part identity differs: ' + name)
        data.append(part)
    original = b''.join(data)
    if len(original) != 16468003 or hashlib.sha256(original).hexdigest() != EXPECTED:
        raise ValueError('Reassembled original ZIP identity differs')
    target = directory / NAME
    with target.open('xb') as f:
        f.write(original)
    print(str(target))
    print('SHA256 ' + EXPECTED)

if __name__ == '__main__':
    main()
