import { loadPyodide } from 'pyodide';

let pyodide: any;

self.onmessage = async (event) => {
  const { id, python } = event.data;

  if (!pyodide) {
    self.postMessage({ id, status: 'loading' });
    pyodide = await loadPyodide({
      indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.22.1/full/',
    });
    await pyodide.loadPackage('numpy');
    await pyodide.loadPackage('pandas');
  }

  try {
    self.postMessage({ id, status: 'running' });
    const result = await pyodide.runPythonAsync(python);
    self.postMessage({ id, status: 'complete', result: result.toString() });
  } catch (error) {
    self.postMessage({ id, status: 'error', error: error.toString() });
  }
};