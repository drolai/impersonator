import torch.nn as nn
import functools
import torch
import torch.nn.functional as F
from torchvision import models
from .hmr import HumanModelRecovery


class NetworksFactory(object):
    def __init__(self):
        pass

    @staticmethod
    def get_by_name(network_name, *args, **kwargs):

        if network_name == 'impersonator':
            from .generator import ImpersonatorGenerator
            network = ImpersonatorGenerator(*args, **kwargs)

        elif network_name == 'impersonator_full':
            from .generator_full import ImpersonatorGenerator
            network = ImpersonatorGenerator(*args, **kwargs)

        elif network_name == 'impersonator_full_aug':
            from .generator_full_aug import ImpersonatorGenerator
            network = ImpersonatorGenerator(*args, **kwargs)

        elif network_name == 'impersonator_adain_warp':
            from .generator_adain_warp import ImpersonatorGenerator
            network = ImpersonatorGenerator(*args, **kwargs)

        elif network_name == 'impersonator_adain_warp_aug':
            from .generator_adain_warp_aug import ImpersonatorAugGenerator
            network = ImpersonatorAugGenerator(*args, **kwargs)

        elif network_name == 'concat':
            from .baseline import ConcatGenerator
            network = ConcatGenerator(*args, **kwargs)

        elif network_name == 'discriminator_patch_gan':
            from .discriminator import PatchDiscriminator
            network = PatchDiscriminator(*args, **kwargs)

        else:
            raise ValueError("Network %s not recognized." % network_name)

        print("Network %s was created" % network_name)

        return network


class NetworkBase(nn.Module):
    def __init__(self):
        super(NetworkBase, self).__init__()
        self._name = 'BaseNetwork'

    @property
    def name(self):
        return self._name

    def init_weights(self):
        self.apply(self._weights_init_fn)

    def _weights_init_fn(self, m):
        classname = m.__class__.__name__
        if classname.find('Conv') != -1:
            m.weight.data.normal_(0.0, 0.02)
            if hasattr(m.bias, 'data'):
                m.bias.data.fill_(0)
        elif classname.find('BatchNorm2d') != -1:
            m.weight.data.normal_(1.0, 0.02)
            m.bias.data.fill_(0)

    def _get_norm_layer(self, norm_type='batch'):
        if norm_type == 'batch':
            norm_layer = functools.partial(nn.BatchNorm2d, affine=True)
        elif norm_type == 'instance':
            norm_layer = functools.partial(nn.InstanceNorm2d, affine=False)
        elif norm_type == 'batchnorm2d':
            norm_layer = nn.BatchNorm2d
        else:
            raise NotImplementedError('normalization layer [%s] is not found' % norm_type)

        return norm_layer

    def forward(self, *input):
        raise NotImplementedError


class Vgg19(torch.nn.Module):
    """
    Sequential(
          (0): Conv2d(3, 64, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))

          (1): ReLU(inplace)
          (2): Conv2d(64, 64, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          (3): ReLU(inplace)
          (4): MaxPool2d(kernel_size=2, stride=2, padding=0, dilation=1, ceil_mode=False)
          (5): Conv2d(64, 128, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))

          (6): ReLU(inplace)
          (7): Conv2d(128, 128, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          (8): ReLU(inplace)
          (9): MaxPool2d(kernel_size=2, stride=2, padding=0, dilation=1, ceil_mode=False)
          (10): Conv2d(128, 256, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))

          (11): ReLU(inplace)
          (12): Conv2d(256, 256, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          (13): ReLU(inplace)
          (14): Conv2d(256, 256, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          (15): ReLU(inplace)
          (16): Conv2d(256, 256, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          (17): ReLU(inplace)
          (18): MaxPool2d(kernel_size=2, stride=2, padding=0, dilation=1, ceil_mode=False)
          (19): Conv2d(256, 512, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))

          (20): ReLU(inplace)
          (21): Conv2d(512, 512, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          (22): ReLU(inplace)
          (23): Conv2d(512, 512, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          (24): ReLU(inplace)
          (25): Conv2d(512, 512, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          (26): ReLU(inplace)
          (27): MaxPool2d(kernel_size=2, stride=2, padding=0, dilation=1, ceil_mode=False)
          (28): Conv2d(512, 512, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))

          (29): ReLU(inplace)
          xxxx(30): Conv2d(512, 512, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          xxxx(31): ReLU(inplace)
          xxxx(32): Conv2d(512, 512, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          xxxx(33): ReLU(inplace)
          xxxx(34): Conv2d(512, 512, kernel_size=(3, 3), stride=(1, 1), padding=(1, 1))
          xxxx(35): ReLU(inplace)
          xxxx(36): MaxPool2d(kernel_size=2, stride=2, padding=0, dilation=1, ceil_mode=False)
    )
    """

    def __init__(self, requires_grad=False, before_relu=False):
        super(Vgg19, self).__init__()
        vgg_pretrained_features = models.vgg19(pretrained=True).features
        print('loading vgg19 ...')

        if before_relu:
            slice_ids = [1, 6, 11, 20, 29]
        else:
            slice_ids = [2, 7, 12, 21, 30]

        self.slice1 = torch.nn.Sequential()
        self.slice2 = torch.nn.Sequential()
        self.slice3 = torch.nn.Sequential()
        self.slice4 = torch.nn.Sequential()
        self.slice5 = torch.nn.Sequential()
        for x in range(slice_ids[0]):
            self.slice1.add_module(str(x), vgg_pretrained_features[x])
        for x in range(slice_ids[0], slice_ids[1]):
            self.slice2.add_module(str(x), vgg_pretrained_features[x])
        for x in range(slice_ids[1], slice_ids[2]):
            self.slice3.add_module(str(x), vgg_pretrained_features[x])
        for x in range(slice_ids[2], slice_ids[3]):
            self.slice4.add_module(str(x), vgg_pretrained_features[x])
        for x in range(slice_ids[3], slice_ids[4]):
            self.slice5.add_module(str(x), vgg_pretrained_features[x])

        if not requires_grad:
            for param in self.parameters():
                param.requires_grad = False

    def forward(self, X):
        h_out1 = self.slice1(X)
        h_out2 = self.slice2(h_out1)
        h_out3 = self.slice3(h_out2)
        h_out4 = self.slice4(h_out3)
        h_out5 = self.slice5(h_out4)
        out = [h_out1, h_out2, h_out3, h_out4, h_out5]
        return out


class VGGLoss(nn.Module):
    def __init__(self, before_relu=False):
        super(VGGLoss, self).__init__()
        self.vgg = Vgg19(before_relu=before_relu).cuda()
        self.criterion = nn.L1Loss()
        self.weights = [1.0/32, 1.0/16, 1.0/8, 1.0/4, 1.0]

    def forward(self, x, y):
        x_vgg, y_vgg = self.vgg(x), self.vgg(y)
        loss = 0
        for i in range(len(x_vgg)):
            loss += self.weights[i] * self.criterion(x_vgg[i], y_vgg[i].detach())
        return loss


class HMRLoss(nn.Module):
    def __init__(self, pretrain_model, smpl_pkl_path):
        super(HMRLoss, self).__init__()
        self.hmr = HumanModelRecovery(smpl_pkl_path=smpl_pkl_path)
        self.load_model(pretrain_model)
        self.criterion = nn.L1Loss()
        self.eval()

    def forward(self, x, y):
        x_hmr, y_hmr = self.hmr(x), self.hmr(y)
        loss = 0.0
        for i in range(len(x_hmr)):
            loss += self.criterion(x_hmr[i], y_hmr[i].detach())
            # loss += self.criterion(x_hmr[i], y_hmr[i])
        return loss

    def load_model(self, pretrain_model):
        saved_data = torch.load(pretrain_model)
        self.hmr.load_state_dict(saved_data)
        print('load hmr model from {}'.format(pretrain_model))


class sphere20a(nn.Module):
    def __init__(self,classnum=10574,feature=False):
        super(sphere20a, self).__init__()
        self.classnum = classnum
        self.feature = feature
        #input = B*3*112*96
        self.conv1_1 = nn.Conv2d(3,64,3,2,1) #=>B*64*56*48
        self.relu1_1 = nn.PReLU(64)
        self.conv1_2 = nn.Conv2d(64,64,3,1,1)
        self.relu1_2 = nn.PReLU(64)
        self.conv1_3 = nn.Conv2d(64,64,3,1,1)
        self.relu1_3 = nn.PReLU(64)

        self.conv2_1 = nn.Conv2d(64,128,3,2,1) #=>B*128*28*24
        self.relu2_1 = nn.PReLU(128)
        self.conv2_2 = nn.Conv2d(128,128,3,1,1)
        self.relu2_2 = nn.PReLU(128)
        self.conv2_3 = nn.Conv2d(128,128,3,1,1)
        self.relu2_3 = nn.PReLU(128)

        self.conv2_4 = nn.Conv2d(128,128,3,1,1) #=>B*128*28*24
        self.relu2_4 = nn.PReLU(128)
        self.conv2_5 = nn.Conv2d(128,128,3,1,1)
        self.relu2_5 = nn.PReLU(128)

        self.conv3_1 = nn.Conv2d(128,256,3,2,1) #=>B*256*14*12
        self.relu3_1 = nn.PReLU(256)
        self.conv3_2 = nn.Conv2d(256,256,3,1,1)
        self.relu3_2 = nn.PReLU(256)
        self.conv3_3 = nn.Conv2d(256,256,3,1,1)
        self.relu3_3 = nn.PReLU(256)

        self.conv3_4 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_4 = nn.PReLU(256)
        self.conv3_5 = nn.Conv2d(256,256,3,1,1)
        self.relu3_5 = nn.PReLU(256)

        self.conv3_6 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_6 = nn.PReLU(256)
        self.conv3_7 = nn.Conv2d(256,256,3,1,1)
        self.relu3_7 = nn.PReLU(256)

        self.conv3_8 = nn.Conv2d(256,256,3,1,1) #=>B*256*14*12
        self.relu3_8 = nn.PReLU(256)
        self.conv3_9 = nn.Conv2d(256,256,3,1,1)
        self.relu3_9 = nn.PReLU(256)

        self.conv4_1 = nn.Conv2d(256,512,3,2,1) #=>B*512*7*6
        self.relu4_1 = nn.PReLU(512)
        self.conv4_2 = nn.Conv2d(512,512,3,1,1)
        self.relu4_2 = nn.PReLU(512)
        self.conv4_3 = nn.Conv2d(512,512,3,1,1)
        self.relu4_3 = nn.PReLU(512)

        self.fc5 = nn.Linear(512*7*6, 512)

    def forward(self, x):
        feat_outs = []
        x = self.relu1_1(self.conv1_1(x))
        x = x + self.relu1_3(self.conv1_3(self.relu1_2(self.conv1_2(x))))
        feat_outs.append(x)

        x = self.relu2_1(self.conv2_1(x))
        x = x + self.relu2_3(self.conv2_3(self.relu2_2(self.conv2_2(x))))
        x = x + self.relu2_5(self.conv2_5(self.relu2_4(self.conv2_4(x))))
        feat_outs.append(x)

        x = self.relu3_1(self.conv3_1(x))
        x = x + self.relu3_3(self.conv3_3(self.relu3_2(self.conv3_2(x))))
        x = x + self.relu3_5(self.conv3_5(self.relu3_4(self.conv3_4(x))))
        x = x + self.relu3_7(self.conv3_7(self.relu3_6(self.conv3_6(x))))
        x = x + self.relu3_9(self.conv3_9(self.relu3_8(self.conv3_8(x))))
        feat_outs.append(x)

        x = self.relu4_1(self.conv4_1(x))
        x = x + self.relu4_3(self.conv4_3(self.relu4_2(self.conv4_2(x))))
        feat_outs.append(x)

        x = x.view(x.size(0), -1)
        x = self.fc5(x)
        feat_outs.append(x)

        return feat_outs


class SphereFaceLoss(nn.Module):

    def __init__(self, pretrained_path='pretrains/sphere20a_20171020.pth', height=112, width=96):
        super(SphereFaceLoss, self).__init__()
        self.net = sphere20a()
        self.load_model(pretrained_path)
        self.eval()
        self.criterion = nn.L1Loss()
        self.weights = [1.0 / 32, 1.0 / 16, 1.0 / 8, 1.0 / 4, 1.0]

        self.height, self.width = height, width

        # from utils.demo_visualizer import MotionImitationVisualizer
        # self._visualizer = MotionImitationVisualizer('debug', ip='http://10.10.10.100', port=31100)

    def forward(self, imgs1, imgs2, kps1=None, kps2=None):
        """
        :param imgs1:
        :param imgs2:
        :param kps1:
        :param kps2:
        :return:
        """
        if kps1 is not None:
            head_imgs1 = self.crop_resize_head(imgs1, kps1)
        elif self.check_need_resize(imgs1):
            head_imgs1 = F.interpolate(imgs1, size=(self.height, self.width), mode='bilinear', align_corners=True)
        else:
            head_imgs1 = imgs1

        if kps2 is not None:
            head_imgs2 = self.crop_resize_head(imgs2, kps2)
        elif self.check_need_resize(imgs2):
            head_imgs2 = F.interpolate(imgs1, size=(self.height, self.width), mode='bilinear', align_corners=True)
        else:
            head_imgs2 = imgs2

        loss = self.compute_loss(head_imgs1, head_imgs2)

        # self._visualizer.vis_named_img('img2', imgs2)
        # self._visualizer.vis_named_img('head imgs2', head_imgs2)
        #
        # self._visualizer.vis_named_img('img1', imgs1)
        # self._visualizer.vis_named_img('head imgs1', head_imgs1)

        return loss

    def compute_loss(self, img1, img2):
        """
        :param img1: (n, 3, 112, 96), [-1, 1]
        :param img2: (n, 3, 112, 96), [-1, 1], if it is used in training,
                     img2 is reference image (GT), use detach() to stop backpropagation.
        :return:
        """
        f1, f2 = self.net(img1), self.net(img2)

        loss = 0.0
        for i in range(len(f1)):
            loss += self.criterion(f1[i], f2[i].detach())

        return loss

    def check_need_resize(self, img):
        return img.shape[2] != self.height or img.shape[3] != self.width

    def crop_resize_head(self, imgs, kps):
        """
        :param imgs: (N, C, H, W)
        :param kps: (N, 19, 2)
        :return:
        """
        bs, _, ori_h, ori_w = imgs.shape

        rects = self.find_head_rect(kps, ori_h, ori_w)
        head_imgs = []

        for i in range(bs):
            min_x, max_x, min_y, max_y = rects[i]
            head = imgs[i:i+1, :, min_y:max_y, min_x:max_x]  # (1, c, h', w')
            head = F.interpolate(head, size=(self.height, self.width), mode='bilinear', align_corners=True)
            head_imgs.append(head)

        head_imgs = torch.cat(head_imgs, dim=0)

        return head_imgs

    @staticmethod
    def find_head_rect(kps, height, width):
        NECK_IDS = 12

        kps = (kps + 1) / 2.0

        necks = kps[:, NECK_IDS, 0]
        zeros = torch.zeros_like(necks)
        ones = torch.ones_like(necks)

        # min_x = int(max(0.0, np.min(kps[HEAD_IDS:, 0]) - 0.1) * image_size)
        min_x, _ = torch.min(kps[:, NECK_IDS:, 0] - 0.05, dim=1)
        min_x = torch.max(min_x, zeros)

        max_x, _ = torch.max(kps[:, NECK_IDS:, 0] + 0.05, dim=1)
        max_x = torch.min(max_x, ones)

        # min_x = int(max(0.0, np.min(kps[HEAD_IDS:, 0]) - 0.1) * image_size)
        min_y, _ = torch.min(kps[:, NECK_IDS:, 1] - 0.05, dim=1)
        min_y = torch.max(min_y, zeros)

        max_y, _ = torch.max(kps[:, NECK_IDS:, 1], dim=1)
        max_y = torch.min(max_y, ones)

        min_x = (min_x * width).long()      # (T, 1)
        max_x = (max_x * width).long()      # (T, 1)
        min_y = (min_y * height).long()     # (T, 1)
        max_y = (max_y * height).long()     # (T, 1)

        # print(min_x.shape, max_x.shape, min_y.shape, max_y.shape)
        rects = torch.stack((min_x, max_x, min_y, max_y), dim=1)

        # import ipdb
        # ipdb.set_trace()

        return rects

    def load_model(self, pretrain_model):
        saved_data = torch.load(pretrain_model)
        save_weights_dict = dict()

        for key, val in saved_data.items():
            if key.startswith('fc6'):
                continue
            save_weights_dict[key] = val

        self.net.load_state_dict(save_weights_dict)

        print('load face model from {}'.format(pretrain_model))


if __name__ == '__main__':
    model = Vgg19(before_relu=True)