import { beforeEach, describe, expect, it, vi } from 'vitest';
import { endpoints } from './api';
import { buildSubmissionPayload, readFileForUpload } from './insuranceDocs';

vi.mock('./api', () => ({ endpoints: { checkLocked: vi.fn() } }));

const file = (bytes, name) => new File([new Uint8Array(bytes)], name);
const ascii = (s) => [...s].map((c) => c.charCodeAt(0));
const OLE = [0xd0, 0xcf, 0x11, 0xe0, 0xa1];
const locked = async (bytes, name) => (await readFileForUpload(file(bytes, name))).locked === true;

describe('password-protected uploads', () => {
  beforeEach(() => {
    endpoints.checkLocked.mockReset();
  });

  it('decides locally when the bytes are conclusive', async () => {
    expect(await locked(OLE, 'a.xlsx')).toBe(true);
    expect(await locked(ascii('PK\x03\x04'), 'a.xlsx')).toBe(false);
    expect(await locked(ascii('%PDF-1.4 trailer<</Root 1 0 R>>'), 'a.pdf')).toBe(false);
    expect(await locked([0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0x01, 0x00], 'pkg.zip')).toBe(true); // encrypted flag set
    expect(await locked([0x50, 0x4b, 0x03, 0x04, 0x14, 0x00, 0x00, 0x00], 'pkg.zip')).toBe(false);
    expect(endpoints.checkLocked).not.toHaveBeenCalled();
  });

  it('asks the server for encrypted-looking PDFs and legacy Office files', async () => {
    endpoints.checkLocked.mockResolvedValue({ locked: ['a.xls'] });
    expect(await locked(OLE, 'a.xls')).toBe(true);

    endpoints.checkLocked.mockResolvedValue({ locked: [] }); // permissions-only PDF
    expect(await locked(ascii('%PDF-1.4 trailer<</Encrypt 6 0 R>>'), 'a.pdf')).toBe(false);
  });

  it('falls back to a guess when the server is unreachable', async () => {
    endpoints.checkLocked.mockRejectedValue(new Error('offline'));
    expect(await locked(ascii('%PDF-1.4 trailer<</Encrypt 6 0 R>>'), 'a.pdf')).toBe(true);
    expect(await locked(OLE, 'a.xls')).toBe(false);
  });

  it('sends the password only when one was entered', () => {
    const { documents } = buildSubmissionPayload([
      { filename: 'a.pdf', content: 'x', encoding: 'base64', locked: true, password: 'secret' },
      { filename: 'b.pdf', content: 'y', encoding: 'base64', locked: true },
    ]);
    expect(documents[0].password).toBe('secret');
    expect('password' in documents[1]).toBe(false);
    expect('locked' in documents[0]).toBe(false);
  });
});
