from src.utils.runner import process_claim, process_swap, process_checker

module_handlers = {
    'CLAIM': process_claim,
    'SWAP': process_swap,
    'CHECK_TOKENS': process_checker
}
