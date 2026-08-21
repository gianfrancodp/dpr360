from .metadata import MetadataStep
from .raw_conversion import RawConversionStep
from .pto_gen import PtoGenStep
from .cpfind import CpFindStep
from .cpclean import CpCleanStep
from .optimise import OptimiseStep
from .panorama_setup import PanoramaSetupStep
from .pto_validation import PtoValidationStep
from .remap import RemapStep
from .blend import BlendStep
from .final_validation import FinalValidationStep

ALL_STEPS = [MetadataStep(), RawConversionStep(), PtoGenStep(), CpFindStep(), CpCleanStep(), OptimiseStep(),
             PanoramaSetupStep(), PtoValidationStep(), RemapStep(), BlendStep(), FinalValidationStep()]
