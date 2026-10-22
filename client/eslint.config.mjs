// ESLint flat config. Next.js 16 removed `next lint`, so `npm run lint` calls the
// ESLint CLI directly with the same `core-web-vitals` rule set the old
// .eslintrc.json extended -- react-hooks/exhaustive-deps included.
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = defineConfig([
  ...nextVitals,
  // Build output and the generated type stub; node_modules is ignored by default.
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);

export default eslintConfig;
