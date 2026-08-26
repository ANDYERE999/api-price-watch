from .new_api import collect_new_api
from .siliconflow import collect_siliconflow
from .sub2api import collect_sub2api
from .x5_pricing_page import collect_x5_pricing_page

COLLECTORS = {
    "new_api": collect_new_api,
    "siliconflow": collect_siliconflow,
    "sub2api": collect_sub2api,
    "x5_pricing_page": collect_x5_pricing_page,
}
