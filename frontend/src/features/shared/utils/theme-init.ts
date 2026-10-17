// Runs before paint; storage may be unavailable in private/restricted browsers.
export const THEME_INIT = `(function(){try{var v=localStorage.getItem('vf_theme');document.documentElement.dataset.theme=v==='dark'||v!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}catch(e){document.documentElement.dataset.theme='light'}})()`;
