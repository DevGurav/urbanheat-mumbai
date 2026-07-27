/**
 * The validated palette (dataviz skill, references/palette.md) — hex values only, no
 * eyeballing. Sequential blue for magnitude (the choropleth layers, `useCityGrid`); the
 * blue↔red diverging pair for polarity (SHAP driver direction: warming vs cooling).
 */

/** Sequential blue, steps 100→700, light→dark. One hue for every choropleth layer — the
 * layer toggle switches which *data* is shown, not which ramp. */
export const SEQUENTIAL_BLUE = [
  "#cde2fb", // 100
  "#b7d3f6", // 150
  "#9ec5f4", // 200
  "#86b6ef", // 250
  "#6da7ec", // 300
  "#5598e7", // 350
  "#3987e5", // 400
  "#2a78d6", // 450
  "#256abf", // 500
  "#1c5cab", // 550
  "#184f95", // 600
  "#104281", // 650
  "#0d366b", // 700
] as const;

/** The diverging pair's poles (palette.md: "blue ↔ red — warm/cool poles"), one step per arm
 * — enough for a two-state direction (warming/cooling), not a full magnitude ramp. */
export const DIVERGING = {
  cooling: "#2a78d6", // sequential step 450 — the same blue, not a second hue
  warming: "#e34948", // categorical slot 8 (red)
} as const;

export const MUTED_INK = "#898781";

/** A value → hex function over [min, max], sequential blue, light = low. Degenerates to the
 * ramp's middle color when every value is equal (no range to speak of). */
export function sequentialScale(min: number, max: number): (value: number) => string {
  if (min === max) {
    return () => SEQUENTIAL_BLUE[Math.floor(SEQUENTIAL_BLUE.length / 2)];
  }
  return (value: number) => {
    const t = Math.min(1, Math.max(0, (value - min) / (max - min)));
    const index = Math.round(t * (SEQUENTIAL_BLUE.length - 1));
    return SEQUENTIAL_BLUE[index];
  };
}
