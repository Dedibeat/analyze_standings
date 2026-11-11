# DE stability development experiment

Research only; not fresh confirmation.

| View | Method | Problems | CF RMSE | Contest-balanced RMSE | Drift RMS |
|---|---|---:|---:|---:|---:|
| full | DE | 185 | 225.61 | 229.29 | 0.00 |
| full | binary_affine | 185 | 246.77 | 252.23 | 0.00 |
| full | augmented | 185 | 237.79 | 239.52 | 0.00 |
| full | stable | 185 | 238.00 | 239.77 | 0.00 |
| half_a0 | DE | 185 | 238.01 | 242.38 | 101.08 |
| half_a0 | binary_affine | 185 | 259.99 | 265.63 | 78.40 |
| half_a0 | augmented | 185 | 225.94 | 229.65 | 97.34 |
| half_a0 | stable | 185 | 227.29 | 231.02 | 95.73 |
| half_b0 | DE | 185 | 240.38 | 245.10 | 81.49 |
| half_b0 | binary_affine | 185 | 255.92 | 261.36 | 67.51 |
| half_b0 | augmented | 185 | 233.39 | 236.82 | 84.06 |
| half_b0 | stable | 185 | 234.26 | 237.72 | 82.46 |
| half_a1 | DE | 185 | 232.18 | 236.89 | 90.28 |
| half_a1 | binary_affine | 185 | 253.85 | 259.54 | 72.85 |
| half_a1 | augmented | 185 | 222.90 | 226.72 | 90.95 |
| half_a1 | stable | 185 | 224.37 | 228.23 | 89.31 |
| half_b1 | DE | 185 | 247.53 | 251.54 | 94.85 |
| half_b1 | binary_affine | 185 | 263.92 | 268.86 | 74.41 |
| half_b1 | augmented | 185 | 237.78 | 240.74 | 91.47 |
| half_b1 | stable | 185 | 238.84 | 241.82 | 90.24 |
| quarter0 | DE | 185 | 295.39 | 298.98 | 206.25 |
| quarter0 | binary_affine | 185 | 291.30 | 296.75 | 149.67 |
| quarter0 | augmented | 185 | 253.87 | 258.25 | 190.57 |
| quarter0 | stable | 185 | 254.63 | 259.06 | 187.40 |
| quarter1 | DE | 185 | 282.53 | 286.74 | 182.58 |
| quarter1 | binary_affine | 185 | 276.81 | 281.69 | 135.18 |
| quarter1 | augmented | 185 | 242.05 | 246.11 | 169.19 |
| quarter1 | stable | 185 | 242.97 | 247.08 | 166.55 |
| half_reserved | DE | 185 | 234.94 | 238.30 | 94.80 |
| half_reserved | binary_affine | 185 | 259.69 | 264.03 | 72.60 |
| half_reserved | augmented | 185 | 225.34 | 227.62 | 96.03 |
| half_reserved | stable | 185 | 226.50 | 228.82 | 94.68 |
| quarter_reserved | DE | 185 | 276.89 | 280.63 | 186.16 |
| quarter_reserved | binary_affine | 185 | 279.23 | 283.88 | 138.49 |
| quarter_reserved | augmented | 185 | 242.49 | 245.43 | 177.43 |
| quarter_reserved | stable | 185 | 243.29 | 246.30 | 175.00 |
| eighth_reserved | DE | 185 | 353.96 | 357.54 | 298.63 |
| eighth_reserved | binary_affine | 185 | 317.64 | 322.38 | 217.25 |
| eighth_reserved | augmented | 185 | 289.56 | 292.93 | 268.51 |
| eighth_reserved | stable | 185 | 289.54 | 293.02 | 264.98 |
| event_only | DE | 185 | 245.05 | 250.14 | 76.09 |
| event_only | binary_affine | 185 | 270.35 | 276.64 | 68.23 |
| event_only | augmented | 185 | 252.01 | 255.72 | 82.19 |
| event_only | stable | 185 | 252.57 | 256.32 | 81.71 |
| event_small | DE | 185 | 310.46 | 312.65 | 207.38 |
| event_small | binary_affine | 185 | 309.35 | 314.00 | 148.63 |
| event_small | augmented | 185 | 273.66 | 277.31 | 185.03 |
| event_small | stable | 185 | 273.83 | 277.51 | 182.33 |
| mirror_balanced | DE | 185 | 264.65 | 267.25 | 149.99 |
| mirror_balanced | binary_affine | 185 | 273.95 | 277.85 | 121.03 |
| mirror_balanced | augmented | 185 | 244.90 | 247.47 | 153.39 |
| mirror_balanced | stable | 185 | 245.72 | 248.35 | 150.41 |
| strength_pool | DE | 185 | 304.87 | 305.73 | 0.00 |
| strength_pool | binary_affine | 185 | 313.67 | 314.86 | 0.00 |
| strength_pool | augmented | 185 | 268.88 | 270.77 | 0.00 |
| strength_pool | stable | 185 | 270.18 | 272.12 | 0.00 |
| strong | DE | 185 | 369.48 | 374.00 | 135.93 |
| strong | binary_affine | 185 | 386.88 | 389.80 | 159.73 |
| strong | augmented | 185 | 327.80 | 333.30 | 134.08 |
| strong | stable | 185 | 327.55 | 333.12 | 131.11 |
| weak | DE | 185 | 450.72 | 449.05 | 231.49 |
| weak | binary_affine | 185 | 381.42 | 383.06 | 157.01 |
| weak | augmented | 185 | 356.99 | 356.76 | 196.63 |
| weak | stable | 185 | 355.70 | 355.54 | 194.52 |

Selected beta=0 in 8/15 folds. Inspect whether the penalty adds
anything beyond augmented ridge. Full predictions, intervals, tail/region errors,
spread and order reversals are in evaluation.json. No production promotion.
