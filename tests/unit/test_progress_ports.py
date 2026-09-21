from modeldock.adapters.progress.rich_progress import RichProgress
from modeldock.adapters.progress.silent import SilentProgress
from modeldock.adapters.progress.tqdm_progress import TqdmProgress

def test_rich_progress_contract():
    port = RichProgress()
    # Verify the port follows the contract methods
    port.start(total=100, desc="Testing Rich")
    port.update(advance=50)
    port.finish()

def test_tqdm_progress_contract():
    port = TqdmProgress()
    port.start(total=100, desc="Testing TQDM")
    port.update(advance=50)
    port.finish()

def test_silent_progress_contract():
    port = SilentProgress()
    # Silent progress might not need all arguments, but it must accept them
    # to fulfill the shared contract.
    port.start(total=100, desc="Testing Silent")
    port.update(advance=50)
    port.finish()