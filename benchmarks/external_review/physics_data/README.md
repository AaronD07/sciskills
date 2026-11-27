# FrontierScience physics

Eight questions use the public FrontierScience Olympiad gold set. Two retain their original numerical inputs and requested precision. Six ask for the value of the published symbolic answer at specified parameters. Each packet contains the original physics question, the numerical measurement and the same JSON submission contract. The parameter choices appear in the manifest and are fixed across all review conditions. The original response-format boilerplate is removed. Each answer is graded in its requested unit with an absolute tolerance of half a unit in the last requested significant place. A single numerical evaluation cannot establish the correctness of an entire symbolic derivation.

OpenAI reports that GPT-5.2 solved 77% of the full Olympiad set using its own evaluation. The developers selected some questions partly on failures of internal models. The public set can have appeared in training. This study measures the change after review on selected public physics questions using deterministic scoring. [OpenAI paper](https://cdn.openai.com/pdf/2fcd284c-b468-4c21-8ee0-7a783933efcc/frontierscience-paper.pdf) · [Dataset and Apache 2.0 license](https://huggingface.co/datasets/openai/frontierscience/tree/647a421c89d15aceaaa1a328e69b950b7632d2cf)

The reference calculations below use the parameters in the manifest. They are kept outside the participant packet.

| Split | Topic | Independent check |
| --- | --- | --- |
| Development | Relativistic acceleration | In the lab, the rear and front follow hyperbolae of radii R = c²/a and R + L. At equal lab time their spatial separation is √((R+L)²+(ct)²) − √(R²+(ct)²), with ct = Rγv/c. This gives 1.87529890 m. |
| Development | Figure-eight orbit | Work in units where d = 242, curvature radius b = 41.7 and o = 145.2. At the central crossing the potential is −2.5 Gm²/(oL) and the kinetic energy is 0.75 m v₀² by symmetry. At the outer point the squared speed is 2Gmb cos θ/(d²L). Momentum and zero angular momentum give kinetic energy m v²(1/2 + 1/(4 sin²θ)). The third pair separation is 2dL sin θ. Conservation of energy gives −8.63957 × 10³⁹ J, consistent with the published two-digit result. |
| Development | Catenary on sliding supports | Write x = b − A cosh(y/A). The free endpoint tension is normal to the supporting rod, so sinh(yₑ/A) = √3. The half-length integral gives A = L/(2√3). Imposing xₑ = yₑ/√3 gives f(2.4 m) = 1.51059107. |
| Holdout | Molecular effusion | The equilibrium gas stores (5/2)NkT. The escaping flux is velocity weighted and carries 2kT in translation plus kT in rotation per molecule. Integrating the energy balance gives 223.59744 K. |
| Holdout | Domain wall | The minimizing profile has equal gradient and potential energy densities. Integrating √(ρκ/2)(M₀²−M²) between the magnetization endpoints gives 2.17738354. |
| Holdout | Charged ellipsoid | A thin homoeoid gives a surface density inversely proportional to √(x²/a⁴ + y²/b⁴ + z²/c⁴). The affine unit-sphere area Jacobian fixes the normalization Q/(4πabc). The specified point lies on the surface, and the result is 0.02244493 nC/cm². |
| Holdout | Ionospheric attenuation | The cold-plasma dispersion relation gives an intensity ratio exp(−2z√(ωₚ²−ω²)/c), with ωₚ² = ne²/(ε₀m). The original density is 2.2 × 10¹⁴ m⁻³. The ratio is 0.19783025, which rounds to the published 0.2. |
| Holdout | London dispersion | The coupled oscillator stiffnesses shift by ±e²/(2πε₀R³). The first-order shifts cancel in their summed zero-point energy. The quadratic term gives 2.16457449 × 10⁻⁷⁹ J m⁶ for C. |

The upstream Olympiad file is small and downloaded once. From the repository root, run `python3 -c 'from benchmarks.external_review.physics import cases; cases("dev")'`. Its pinned SHA-256 is checked on every new process. The default cache is `~/.cache/sciskills/frontierscience`. Set `SCISKILLS_FRONTIERSCIENCE_CACHE` to choose another cache root.
