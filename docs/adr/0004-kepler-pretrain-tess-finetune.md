# ADR-0004: Kepler pre-training + TESS fine-tuning over TESS-only

The CNN is pre-trained on the Kepler DR24 labeled dataset (34,032 TCEs from Thompson et al. 2018) and fine-tuned on ExoFOP-TESS TOI labels, rather than trained exclusively on TESS data.

**Why**: Kepler provides 4 years of continuous photometry per star with no data gaps — the CNN learns transit morphology from cleaner, denser signals before adapting to TESS-specific noise. This is the proven pattern used by ExoMiner++ (Valizadegan et al. 2025, NASA's production classifier). The combined dataset (~51k real samples before augmentation) provides more training signal than TESS-only (~17k). Fine-tuning handles the domain gap between Kepler and TESS instrumentals, cadences, and systematics. The TIC/MAST bulk download (the must-use dataset) serves as the fine-tuning and inference data source.

**Rejected**: TESS-only training — avoids cross-mission domain adaptation but loses the 34k Kepler samples and the stronger shape prior they provide. The TESS-only catalog (~17k ExoFOP labels) is sufficient for a basic classifier but leaves shallow-transit detection accuracy lower without the richer Kepler morphology signal.

**Status**: accepted
