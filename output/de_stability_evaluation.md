# DE stability development experiment

Research only; not fresh confirmation.

| View | Method | Problems | CF RMSE | Contest-balanced RMSE | Drift RMS |
|---|---|---:|---:|---:|---:|
| full | DE | 185 | 225.61 | 229.29 | 0.00 |
| full | binary_affine | 185 | 246.78 | 252.24 | 0.00 |
| full | augmented | 185 | 237.78 | 239.51 | 0.00 |
| full | stable | 185 | 237.99 | 239.76 | 0.00 |
| half_a0 | DE | 185 | 238.02 | 242.39 | 101.07 |
| half_a0 | binary_affine | 185 | 260.00 | 265.65 | 78.42 |
| half_a0 | augmented | 185 | 225.96 | 229.67 | 97.38 |
| half_a0 | stable | 185 | 227.32 | 231.05 | 95.76 |
| half_b0 | DE | 185 | 240.36 | 245.09 | 81.44 |
| half_b0 | binary_affine | 185 | 255.93 | 261.37 | 67.51 |
| half_b0 | augmented | 185 | 233.39 | 236.82 | 84.10 |
| half_b0 | stable | 185 | 234.26 | 237.73 | 82.49 |
| half_a1 | DE | 185 | 232.16 | 236.87 | 90.20 |
| half_a1 | binary_affine | 185 | 253.84 | 259.53 | 72.81 |
| half_a1 | augmented | 185 | 222.91 | 226.74 | 90.95 |
| half_a1 | stable | 185 | 224.39 | 228.25 | 89.30 |
| half_b1 | DE | 185 | 247.51 | 251.52 | 94.83 |
| half_b1 | binary_affine | 185 | 263.96 | 268.89 | 74.44 |
| half_b1 | augmented | 185 | 237.78 | 240.74 | 91.53 |
| half_b1 | stable | 185 | 238.84 | 241.82 | 90.29 |
| quarter0 | DE | 185 | 295.38 | 298.97 | 206.23 |
| quarter0 | binary_affine | 185 | 291.32 | 296.78 | 149.70 |
| quarter0 | augmented | 185 | 253.87 | 258.26 | 190.54 |
| quarter0 | stable | 185 | 254.64 | 259.07 | 187.37 |
| quarter1 | DE | 185 | 282.49 | 286.71 | 182.43 |
| quarter1 | binary_affine | 185 | 276.83 | 281.72 | 135.11 |
| quarter1 | augmented | 185 | 242.15 | 246.22 | 169.20 |
| quarter1 | stable | 185 | 243.06 | 247.18 | 166.54 |
| half_reserved | DE | 185 | 234.90 | 238.27 | 94.70 |
| half_reserved | binary_affine | 185 | 259.69 | 264.04 | 72.56 |
| half_reserved | augmented | 185 | 225.36 | 227.64 | 96.05 |
| half_reserved | stable | 185 | 226.52 | 228.84 | 94.69 |
| quarter_reserved | DE | 185 | 276.77 | 280.52 | 185.92 |
| quarter_reserved | binary_affine | 185 | 279.24 | 283.89 | 138.40 |
| quarter_reserved | augmented | 185 | 242.53 | 245.47 | 177.35 |
| quarter_reserved | stable | 185 | 243.33 | 246.34 | 174.90 |
| eighth_reserved | DE | 185 | 353.73 | 357.33 | 298.29 |
| eighth_reserved | binary_affine | 185 | 317.64 | 322.39 | 217.17 |
| eighth_reserved | augmented | 185 | 289.54 | 292.91 | 268.30 |
| eighth_reserved | stable | 185 | 289.52 | 293.00 | 264.77 |
| event_only | DE | 185 | 245.04 | 250.14 | 76.06 |
| event_only | binary_affine | 185 | 270.39 | 276.68 | 68.26 |
| event_only | augmented | 185 | 252.00 | 255.71 | 82.21 |
| event_only | stable | 185 | 252.57 | 256.32 | 81.73 |
| event_small | DE | 185 | 310.33 | 312.53 | 207.19 |
| event_small | binary_affine | 185 | 309.38 | 314.03 | 148.65 |
| event_small | augmented | 185 | 273.65 | 277.30 | 184.99 |
| event_small | stable | 185 | 273.82 | 277.51 | 182.29 |
| mirror_balanced | DE | 185 | 264.60 | 267.21 | 149.93 |
| mirror_balanced | binary_affine | 185 | 273.92 | 277.83 | 121.01 |
| mirror_balanced | augmented | 185 | 244.92 | 247.50 | 153.41 |
| mirror_balanced | stable | 185 | 245.74 | 248.37 | 150.40 |
| strength_pool | DE | 185 | 304.85 | 305.71 | 0.00 |
| strength_pool | binary_affine | 185 | 313.85 | 315.04 | 0.00 |
| strength_pool | augmented | 185 | 268.90 | 270.80 | 0.00 |
| strength_pool | stable | 185 | 270.19 | 272.15 | 0.00 |
| strong | DE | 185 | 369.40 | 373.93 | 135.80 |
| strong | binary_affine | 185 | 386.91 | 389.83 | 159.66 |
| strong | augmented | 185 | 327.77 | 333.28 | 133.94 |
| strong | stable | 185 | 327.52 | 333.10 | 130.98 |
| weak | DE | 185 | 450.91 | 448.98 | 231.90 |
| weak | binary_affine | 185 | 381.80 | 383.03 | 156.70 |
| weak | augmented | 185 | 356.71 | 355.99 | 196.27 |
| weak | stable | 185 | 355.43 | 354.77 | 194.09 |

Selected beta=0 in 8/15 folds. Inspect whether the penalty adds
anything beyond augmented ridge. Full predictions, intervals, tail/region errors,
spread and order reversals are in evaluation.json. No production promotion.
