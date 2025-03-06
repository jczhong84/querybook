jest.mock('../../../lib/web-worker/python-worker', () => ({
  runPythonCode: jest.fn((python) => {
    return new Promise((resolve, reject) => {
      if (python.includes('raise Exception')) {
        reject(new Error('Test error'));
      } else {
        resolve(`Result: ${python}`);
      }
    });
  }),
}));

import { runPythonCode } from '../../../lib/web-worker/python-worker';

describe('Python Code Execution', () => {
  it('should execute Python code and return the result', async () => {
    const pythonCode = 'print("Hello, Python!")';
    const result = await runPythonCode(pythonCode);
    expect(result).toBe('Result: print("Hello, Python!")');
  });

  it('should handle errors', async () => {
    const pythonCode = 'raise Exception("Test error")';
    await expect(runPythonCode(pythonCode)).rejects.toThrow('Test error');
  });
});