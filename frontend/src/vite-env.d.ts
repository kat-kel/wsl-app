/// <reference types="vite/client" />

// Deliberately no ImportMetaEnv declarations. Nothing in this app reads
// import.meta.env: the API base is the relative path "/api" (see src/api/),
// so the compiled bundle names no environment. A VITE_-prefixed variable
// would be inlined into that bundle at build time, which is the opposite of
// what we want -- the proxy target is resolved when a container starts, by
// Vite's dev server locally and by Nginx in the cloud.
