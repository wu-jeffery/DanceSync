# === Ultralytics YOLOv8 Core ===
from ultralytics.nn.tasks import PoseModel
from ultralytics.nn.modules.conv import Conv, Concat
from ultralytics.nn.modules.block import Bottleneck, C2f, SPPF, DFL
from ultralytics.nn.modules.head import Pose, Detect

# === PyTorch Modules ===
from torch.nn import Conv2d, BatchNorm2d, SiLU
from torch.nn.modules.pooling import MaxPool2d
from torch.nn.modules.upsampling import Upsample
from torch.nn.modules.container import ModuleList, Sequential
import torch.serialization

def setup_torch_safe_globals():
    """Register all modules required to safely load YOLOv8 pose models in PyTorch 2.6+"""
    torch.serialization.add_safe_globals([
        # Ultralytics model components
        PoseModel,
        Conv,
        Concat,
        Bottleneck,
        C2f,
        SPPF,
        DFL,
        Pose,
        Detect,

        # Standard PyTorch layers
        Conv2d,
        BatchNorm2d,
        SiLU,
        MaxPool2d,
        Upsample,
        ModuleList,
        Sequential,

        # Built-ins used in model deserialization
        getattr
    ])
