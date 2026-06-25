# ADR-0001: Dual-View CNN over Bi-LSTM + Transformer

The classifier uses a Dual-View 1D CNN (AstroNet, Shallue & Vanderburg 2018) rather than the Bi-LSTM + Transformer ensemble proposed in the submission document.

**Why**: The CNN architecture is peer-reviewed (published in AJ 155, 94), has known behavior on transit classification, and judges will recognize it as the state-of-the-art foundation. The Bi-LSTM + Transformer is novel — the submission document describes it as an original proposal without a supporting paper. CNN training completes in <2 hours on a T4 GPU (comparable to the 1.2M-parameter Bi-LSTM claim). The 2.5M vs. 1.2M parameter difference is immaterial at this scale. TensorFlow/Keras provides a simpler, more battle-tested API for 1D CNNs than PyTorch's LSTM/Transformer stack.

**Rejected**: Bi-LSTM + Transformer ensemble — lacks peer-reviewed backing, complicates the codebase with two frameworks (PyTorch for Transformer, TensorFlow/Keras for CNN), and the claimed asymmetric-signal sensitivity advantage is also achievable via the CNN's local-zoom view.

**Status**: accepted
