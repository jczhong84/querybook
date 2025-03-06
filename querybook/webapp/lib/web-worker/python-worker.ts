const PYODIDE_WORKER_URL = '/python-worker/pyodideWorker.ts';
const pyodideWorker = typeof Worker !== 'undefined' ? new Worker(PYODIDE_WORKER_URL) : null;

export const runPythonCode = (python: string): Promise<string> => {
  return new Promise((resolve, reject) => {
    const id = Date.now().toString();
    
    const handleMessage = (event: MessageEvent) => {
      if (event.data.id === id) {
        if (event.data.status === 'complete') {
          pyodideWorker.removeEventListener('message', handleMessage);
          resolve(event.data.result);
        } else if (event.data.status === 'error') {
          pyodideWorker.removeEventListener('message', handleMessage);
          reject(new Error(event.data.error));
        }
      }
    };

    pyodideWorker.addEventListener('message', handleMessage);
    pyodideWorker.postMessage({ id, python });
  });
};