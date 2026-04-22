import sys
from pathlib import Path
import numpy as np

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.mlab import _spectral_helper


class TestMlabSpectralHelperDefUsePairsQA:
    def test_mlab_spectral_helper_def_use_pairs_case(self):
        # Test 1: Simple PSD with defaults
        x = np.random.randn(512)
        result, freqs, t = _spectral_helper(x, mode='psd')
        assert result.shape[0] > 0
        assert len(freqs) > 0
        
        # Test 2: Cross-spectral density
        x = np.random.randn(512)
        y = np.random.randn(512)
        result, freqs, t = _spectral_helper(x, y, mode='psd')
        assert result is not None
        
        # Test 3: Custom NFFT
        x = np.random.randn(1024)
        result, freqs, t = _spectral_helper(x, NFFT=256, mode='psd')
        assert len(freqs) > 0
        
        # Test 4: With overlap
        x = np.random.randn(512)
        result, freqs, t = _spectral_helper(x, NFFT=128, noverlap=64, mode='psd')
        assert result.shape[1] > 1
        
        # Test 5: Custom sampling frequency
        x = np.random.randn(512)
        result, freqs, t = _spectral_helper(x, Fs=1000, mode='psd')
        assert freqs[-1] > 0
        
        # Test 6: Magnitude mode
        x = np.random.randn(256)
        result, freqs, t = _spectral_helper(x, mode='magnitude')
        assert result is not None
        
        # Test 7: Angle mode
        x = np.random.randn(256) + 1j * np.random.randn(256)
        result, freqs, t = _spectral_helper(x, mode='angle')
        assert result is not None
        
        # Test 8: Complex mode
        x = np.random.randn(256)
        result, freqs, t = _spectral_helper(x, mode='complex')
        assert result is not None
        
        # Test 9: Two-sided spectrum
        x = np.random.randn(256) + 1j * np.random.randn(256)
        result, freqs, t = _spectral_helper(x, sides='twosided', mode='psd')
        assert len(freqs) > 100
        
        # Test 10: Scale by frequency
        x = np.random.randn(512)
        result, freqs, t = _spectral_helper(x, scale_by_freq=True, mode='psd')
        assert result is not None
        
        # Test 11: Custom padding
        x = np.random.randn(256)
        result, freqs, t = _spectral_helper(x, NFFT=128, pad_to=256, mode='psd')
        assert len(freqs) > 0
        
        # Test 12: Short signal with padding
        x = np.random.randn(50)
        result, freqs, t = _spectral_helper(x, NFFT=128, mode='psd')
        assert result is not None
