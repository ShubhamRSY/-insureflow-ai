import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import RunSelector from './RunSelector';

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual('../lib/api');
  return { ...actual, endpoints: { checkLocked: vi.fn(), validateDocuments: vi.fn() } };
});
vi.mock('../lib/useStateContext', () => ({ useStateContext: () => ({ selectedState: null }) }));
vi.mock('./ConnectAndPull', () => ({ default: () => null }));

import { endpoints } from '../lib/api';

const ascii = (s) => new Uint8Array([...s].map((c) => c.charCodeAt(0)));
const lockedPdf = () => new File([ascii('%PDF-1.4\n%loss run\ntrailer<</Encrypt 6 0 R/Root 1 0 R>>')], 'loss_run.pdf', { type: 'application/pdf' });
const plainPdf = () => new File([ascii('%PDF-1.4\ntrailer<</Root 1 0 R>>')], 'sov.pdf', { type: 'application/pdf' });

function upload(container, ...files) {
  fireEvent.change(container.querySelector('input[type="file"]'), { target: { files } });
}

describe('RunSelector — password-protected uploads', () => {
  beforeEach(() => {
    endpoints.checkLocked.mockReset().mockResolvedValue({ locked: ['loss_run.pdf'] });
    endpoints.validateDocuments.mockReset().mockResolvedValue({ can_run: true, irrelevant: [], warnings: [] });
  });

  it('asks for a password only on the locked file and sends it with the run', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const { container } = render(<RunSelector vertical="lending" onSubmit={onSubmit} />);

    upload(container, lockedPdf(), plainPdf());

    const password = await screen.findByLabelText('Password for loss_run.pdf');
    expect(screen.queryByLabelText('Password for sov.pdf')).toBeNull();
    expect(password).toHaveProperty('type', 'password');

    fireEvent.change(password, { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /Run pipeline/ }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    const { documents } = onSubmit.mock.calls[0][0];
    expect(documents.find((d) => d.filename === 'loss_run.pdf').password).toBe('secret');
    expect('password' in documents.find((d) => d.filename === 'sov.pdf')).toBe(false);
  });

  it('shows no password box when the server says the PDF opens without one', async () => {
    endpoints.checkLocked.mockResolvedValue({ locked: [] }); // e.g. print/copy-restricted only
    const { container } = render(<RunSelector vertical="lending" onSubmit={vi.fn()} />);

    upload(container, lockedPdf());

    await screen.findByText('loss_run.pdf');
    expect(screen.queryByLabelText('Password for loss_run.pdf')).toBeNull();
  });
});
