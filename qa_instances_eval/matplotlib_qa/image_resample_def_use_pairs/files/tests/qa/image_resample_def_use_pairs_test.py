import sys
from pathlib import Path
import numpy as np
from unittest.mock import Mock, MagicMock

# CRITICAL: Force local matplotlib import
testbed_path = Path("/testbed")
lib_path = testbed_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Now import from local source
from matplotlib.image import _resample
from matplotlib.transforms import Affine2D


class TestImageResampleDefUsePairsQA:
    def test_image_resample_def_use_pairs_case(self):
        # Create mock image object with necessary attributes
        def create_mock_image(interpolation='nearest', resample=True, 
                            filternorm=True, filterrad=4.0):
            mock_img = Mock()
            mock_img.get_interpolation = Mock(return_value=interpolation)
            mock_img.get_resample = Mock(return_value=resample)
            mock_img.get_filternorm = Mock(return_value=filternorm)
            mock_img.get_filterrad = Mock(return_value=filterrad)
            return mock_img
        
        # Test 1: Small RGBA data, nearest interpolation
        data1 = np.random.rand(10, 10, 4)
        transform1 = Affine2D()
        mock_img1 = create_mock_image('nearest')
        result1 = _resample(mock_img1, data1, (20, 20), transform1)
        assert result1.shape == (20, 20, 4)
        
        # Test 2: antialiased interpolation (triggers complex conditionals)
        data2 = np.random.rand(50, 50, 4)
        transform2 = Affine2D().scale(2.0, 2.0)  # 2x upsampling
        mock_img2 = create_mock_image('antialiased')
        result2 = _resample(mock_img2, data2, (100, 100), transform2)
        assert result2.shape == (100, 100, 4)
        
        # Test 3: auto interpolation with small zoom
        data3 = np.random.rand(30, 30, 4)
        transform3 = Affine2D().scale(1.5, 1.5)
        mock_img3 = create_mock_image('auto')
        result3 = _resample(mock_img3, data3, (45, 45), transform3)
        assert result3.shape == (45, 45, 4)
        
        # Test 4: Large zoom (>3x) - triggers nearest interpolation path
        data4 = np.random.rand(20, 20, 4)
        transform4 = Affine2D().scale(4.0, 4.0)  # 4x upsampling
        mock_img4 = create_mock_image('antialiased')
        result4 = _resample(mock_img4, data4, (80, 80), transform4)
        assert result4.shape == (80, 80, 4)
        
        # Test 5: Exact 1x upsampling - triggers nearest
        data5 = np.random.rand(40, 40, 4)
        transform5 = Affine2D()  # No scaling
        mock_img5 = create_mock_image('antialiased')
        result5 = _resample(mock_img5, data5, (40, 40), transform5)
        assert result5.shape == (40, 40, 4)
        
        # Test 6: 2x upsampling - triggers nearest
        data6 = np.random.rand(25, 25, 4)
        transform6 = Affine2D().scale(2.0, 2.0)
        mock_img6 = create_mock_image('auto')
        result6 = _resample(mock_img6, data6, (50, 50), transform6)
        assert result6.shape == (50, 50, 4)
        
        # Test 7: Grayscale (2D) data
        data7 = np.random.rand(15, 15)
        transform7 = Affine2D().scale(1.8, 1.8)
        mock_img7 = create_mock_image('bilinear')
        result7 = _resample(mock_img7, data7, (27, 27), transform7)
        assert result7.shape == (27, 27)
        
        # Test 8: With explicit resample parameter
        data8 = np.random.rand(20, 20, 4)
        transform8 = Affine2D()
        mock_img8 = create_mock_image('nearest', resample=False)
        result8 = _resample(mock_img8, data8, (30, 30), transform8, resample=True)
        assert result8.shape == (30, 30, 4)
        
        # Test 9: Different filterrad
        data9 = np.random.rand(12, 12, 4)
        transform9 = Affine2D().scale(2.5, 2.5)
        mock_img9 = create_mock_image('hanning', filterrad=6.0)
        result9 = _resample(mock_img9, data9, (30, 30), transform9)
        assert result9.shape == (30, 30, 4)
        
        # Test 10: Complex transform (rotation + scale)
        data10 = np.random.rand(18, 18, 4)
        transform10 = Affine2D().rotate_deg(45).scale(1.5, 1.5)
        mock_img10 = create_mock_image('gaussian')
        result10 = _resample(mock_img10, data10, (27, 27), transform10)
        assert result10.shape == (27, 27, 4)
        
        # Validate all results are numpy arrays
        assert all(isinstance(r, np.ndarray) for r in [
            result1, result2, result3, result4, result5,
            result6, result7, result8, result9, result10
        ])
