// Mirrors src/insureflow/underwriting/actuarial_tables.py (CSO 2017 tables +
// linear-interpolation lookup) so the exploratory Premium Calculator can
// recompute a base mortality rate live as age/tobacco class change, instead
// of freezing on whatever rate the pipeline happened to compute once for the
// case's original inputs. Keep these tables in sync with the Python source —
// this is the one place the frontend duplicates them, specifically to give
// the what-if calculator instant, no-round-trip feedback.

const CSO_2017_NONTOBACCO = {
  15: 0.162, 20: 0.193, 25: 0.228, 30: 0.312, 35: 0.468, 40: 0.726,
  45: 1.179, 50: 1.946, 55: 3.252, 60: 5.478, 65: 9.188, 70: 15.342,
  75: 25.567, 80: 42.213, 85: 69.824, 90: 113.456, 95: 180.234, 99: 275.000,
};

const CSO_2017_TOBACCO = {
  15: 0.289, 20: 0.387, 25: 0.521, 30: 0.752, 35: 1.143, 40: 1.838,
  45: 3.028, 50: 5.041, 55: 8.452, 60: 14.213, 65: 23.678, 70: 39.124,
  75: 63.456, 80: 101.234, 85: 155.678, 90: 234.567, 95: 345.678, 99: 500.000,
};

function interpolateRate(table, age) {
  const ages = Object.keys(table).map(Number).sort((a, b) => a - b);
  if (age <= ages[0]) return table[ages[0]];
  if (age >= ages[ages.length - 1]) return table[ages[ages.length - 1]];
  for (let i = 0; i < ages.length - 1; i += 1) {
    const low = ages[i];
    const high = ages[i + 1];
    if (age >= low && age <= high) {
      if (low === high) return table[low];
      const ratio = (age - low) / (high - low);
      return table[low] + ratio * (table[high] - table[low]);
    }
  }
  return table[ages[ages.length - 1]];
}

// tobaccoStatus: 'tobacco' | 'nontobacco' — matches the Premium Calculator's own select values.
export function lookupBaseRate(age, tobaccoStatus) {
  const table = tobaccoStatus === 'tobacco' ? CSO_2017_TOBACCO : CSO_2017_NONTOBACCO;
  return interpolateRate(table, Number(age) || 0);
}
