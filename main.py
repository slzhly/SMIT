from __future__ import print_function
from misc.utils import PRINT, config_yaml
import os
from data_loader import get_loader
import config as cfg
import warnings
import sys
import torch
from misc.utils import horovod
hvd = horovod()
warnings.filterwarnings('ignore')


def _PRINT(config):
    string = '------------ Options -------------'
    PRINT(config.log, string)
    for k, v in sorted(vars(config).items()):
        string = '%s: %s' % (str(k), str(v))
        PRINT(config.log, string)
    string = '-------------- End ----------------'
    PRINT(config.log, string)


def main(config):
    from torch.backends import cudnn
    # For fast training
    cudnn.benchmark = True
    # cudnn.deterministic = True

    data_loader = get_loader(
        config.mode_data,
        config.image_size,
        config.batch_size,
        config.dataset_fake,
        config.mode,
        num_workers=config.num_workers,
        all_attr=config.ALL_ATTR,
        c_dim=config.c_dim)

    if config.LPIPS_REAL:
        from scores import Scores
        scores = Scores(config)
        scores.LPIPS_REAL()
        return

    if config.LPIPS_UNIMODAL:
        from scores import Scores
        scores = Scores(config)
        scores.LPIPS_UNIMODAL()
        return

    if config.LPIPS_MULTIMODAL:
        from scores import Scores
        scores = Scores(config)
        scores.LPIPS_MULTIMODAL()
        return

    if config.INCEPTION:
        from scores import Scores
        scores = Scores(config)
        scores.INCEPTION()
        return

    if config.INCEPTION_REAL:
        from scores import Scores
        scores = Scores(config)
        scores.INCEPTION_REAL()
        return

    if config.mode == 'train':
        from train import Train
        Train(config, data_loader)
        from test import Test
        test = Test(config, data_loader)
        test(dataset=config.dataset_real)

    elif config.mode == 'test':
        from test import Test
        test = Test(config, data_loader)
        if config.DEMO_PATH:
            test.DEMO(config.DEMO_PATH)
        else:
            test(dataset=config.dataset_real)


if __name__ == '__main__':

    from options import base_parser
    config = base_parser()

    if config.GPU == '-1':
        # Horovod
        torch.cuda.set_device(hvd.local_rank())
        config.GPU = [int(i) for i in range(hvd.size())]
        config.g_lr *= hvd.size()
        config.d_lr *= hvd.size()

    else:
        if config.GPU == 'NO_CUDA':
            config.GPU = '-1'
        os.environ["CUDA_VISIBLE_DEVICES"] = config.GPU
        config.GPU = [int(i) for i in config.GPU.split(',')]
        config.batch_size *= len(config.GPU)
        config.g_lr *= len(config.GPU)
        config.d_lr *= len(config.GPU)

    torch.manual_seed(config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.seed)

    config_yaml(config, 'datasets/{}.yaml'.format(config.dataset_fake))
    config = cfg.update_config(config)
    if config.mode == 'train':
        if hvd.rank() == 0:
            PRINT(config.log, ' '.join(sys.argv))
            _PRINT(config)
        main(config)
        config.log.close()

    else:
        main(config)
