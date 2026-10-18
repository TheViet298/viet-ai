const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
exports.loader = async function (overrides = {}) {
  const markdown = await import('react-markdown');
  const gfm = await import('remark-gfm');
  const cache = new Map();
  function load(file) {
    file = path.resolve(__dirname, '../src', file);
    if (!path.extname(file)) file = ['.ts', '.tsx'].map(ext => file + ext).find(fs.existsSync);
    if (cache.has(file)) return cache.get(file).exports;
    const module = { exports: {} }; cache.set(file, module);
    const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: {
      module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020, esModuleInterop: true,
    }}).outputText;
    vm.runInNewContext(code, { module, exports: module.exports, Date, console, process, URLSearchParams,
      setTimeout, clearTimeout, setInterval, clearInterval,
      require(id) {
        if (Object.hasOwn(overrides,id)) return overrides[id];
        if (id === 'react-markdown') return {__esModule: true, ...markdown};
        if (id === 'remark-gfm') return {__esModule: true, ...gfm};
        if (id.startsWith('@/')) return load(id.slice(2));
        if (id.startsWith('.')) return load(path.resolve(path.dirname(file), id));
        return require(id);
      },
    }, { filename: file });
    return module.exports;
  }
  return load;
};
