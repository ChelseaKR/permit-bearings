export function median(values) {
  if (values.length === 0) {
    throw new Error("median requires at least one score");
  }
  const ordered = [...values].sort((left, right) => left - right);
  return ordered[Math.floor(ordered.length / 2)];
}
