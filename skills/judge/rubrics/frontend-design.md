# Frontend Design Evaluation Rubric

## Overview
This rubric evaluates the quality of frontend/UI design skill outputs. Use it when the skill under evaluation generates HTML, CSS, JavaScript, or complete UI components. A good frontend output is visually correct, responsive, accessible, and runs without modification.

## Dimension Criteria

### Correctness (Weight: 25%)
**What it measures in this domain:** Whether the generated HTML, CSS, and JavaScript are syntactically valid and produce the intended visual result.

| Score | Criteria |
|-------|----------|
| 9-10  | Valid HTML5, well-formed CSS, error-free JS. Renders correctly across major browsers. Visual output matches intent perfectly. |
| 7-8   | Minor validation warnings but no functional impact. Renders correctly in modern browsers. Visual output is very close to intent. |
| 5-6   | Some validation errors. Renders acceptably in most browsers but with minor visual glitches. |
| 3-4   | Multiple validation errors causing rendering issues. Visual output deviates significantly from intent in some browsers. |
| 1-2   | Code is broken. Does not render correctly. Major syntax errors prevent the page from loading. |

### Completeness (Weight: 20%)
**What it measures in this domain:** Whether the output includes responsive design, accessibility features, and all requested UI states.

| Score | Criteria |
|-------|----------|
| 9-10  | Fully responsive (mobile, tablet, desktop). WCAG 2.1 AA accessible. All UI states covered (hover, focus, error, loading, empty). |
| 7-8   | Responsive at common breakpoints. Basic accessibility in place (alt text, ARIA labels). Most UI states covered. |
| 5-6   | Works at one or two screen sizes. Minimal accessibility. Key UI states present but edge states missing. |
| 3-4   | Only works at a single viewport size. No accessibility considerations. Several UI states missing. |
| 1-2   | Fixed dimensions with no responsiveness. No accessibility. Only the default state implemented. |

### Adherence (Weight: 15%)
**What it measures in this domain:** Whether the output follows the specified design system, brand guidelines, framework conventions, and requested specifications.

| Score | Criteria |
|-------|----------|
| 9-10  | Perfectly matches design spec. Uses specified framework correctly. Follows naming conventions and file structure. |
| 7-8   | Closely matches spec with minor deviations. Framework used correctly. Mostly follows conventions. |
| 5-6   | Generally matches intent but takes liberties with design details. Some framework misuse. |
| 3-4   | Significant deviation from spec. Wrong framework patterns or incorrect component usage. |
| 1-2   | Ignores design spec entirely. Wrong framework or fundamentally wrong approach. |

### Actionability (Weight: 15%)
**What it measures in this domain:** Whether the generated code can be dropped into a project and run without modification.

| Score | Criteria |
|-------|----------|
| 9-10  | Code runs immediately. All dependencies declared. No placeholder values. Copy-paste ready. |
| 7-8   | Code runs with trivial setup (e.g., npm install). Minor config adjustments may be needed. |
| 5-6   | Code runs after moderate setup. Some hardcoded values need replacing. Missing a few imports. |
| 3-4   | Code requires significant modification to run. Missing dependencies, broken imports, or incomplete setup. |
| 1-2   | Code does not run. Major pieces missing. Would need to be rewritten from scratch. |

### Efficiency (Weight: 10%)
**What it measures in this domain:** Whether the code is performant, avoids unnecessary DOM manipulation, and uses optimized assets.

| Score | Criteria |
|-------|----------|
| 9-10  | Lean CSS with no unused rules. Efficient JS with no unnecessary re-renders. Optimized image references. Minimal bundle size. |
| 7-8   | Mostly efficient. Minor unused styles or slightly verbose JS that does not impact performance. |
| 5-6   | Some bloat. Unused CSS rules, redundant DOM queries, or unnecessarily large dependencies. |
| 3-4   | Significant performance issues. Layout thrashing, excessive re-renders, or massive unused CSS. |
| 1-2   | Severe performance problems. Memory leaks, blocking scripts, or egregiously large bundle. |

### Safety (Weight: 10%)
**What it measures in this domain:** Whether the output is free from XSS vectors, unsafe innerHTML usage, and other frontend security risks.

| Score | Criteria |
|-------|----------|
| 9-10  | No XSS vectors. All user input sanitized. CSP-compatible. No inline event handlers with dynamic content. |
| 7-8   | No XSS vectors in primary flows. Minor use of innerHTML with static content only. |
| 5-6   | Some unsanitized user input paths but not in critical flows. Could be tightened. |
| 3-4   | Direct innerHTML usage with user-supplied data. Missing input sanitization on forms. |
| 1-2   | Active XSS vulnerabilities. Eval of user input. Direct DOM injection of unsanitized data. |

### Consistency (Weight: 5%)
**What it measures in this domain:** Whether the code maintains consistent naming, styling patterns, and component structure throughout.

| Score | Criteria |
|-------|----------|
| 9-10  | Uniform naming (BEM, camelCase, etc.). Consistent spacing, color usage, and component patterns. |
| 7-8   | Mostly consistent. Minor naming or style deviations that do not affect readability. |
| 5-6   | Mixed naming conventions. Some inconsistency in spacing or color values between components. |
| 3-4   | Clearly inconsistent. Different patterns used in different sections with no rationale. |
| 1-2   | No consistency. Code appears to mix multiple different style guides randomly. |

## Red Flags (Auto-Deductions)
- No mobile/responsive support whatsoever
- WCAG accessibility violations (missing alt text, no keyboard navigation, insufficient contrast)
- Broken layout at common viewport sizes (320px, 768px, 1024px, 1440px)
- XSS vulnerability from unsanitized user input
- Hardcoded pixel values where relative units are needed
- Missing form labels or interactive element focus states
- Images without alt attributes

## Domain-Specific Bonuses
- Implements smooth, performant animations/transitions
- Includes dark mode support
- Supports reduced-motion preferences
- Uses CSS custom properties for theming
- Implements skeleton loading states
- Progressive enhancement approach (works without JS where appropriate)
- Includes print stylesheet considerations
