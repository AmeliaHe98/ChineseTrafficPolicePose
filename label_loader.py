import os
import pickle
import json
import random
import bidirectional_resize as bir
import numpy as np
import cv2

def load_aicha(folder_path):
    """
    Load AI_Challenger annotations to list
    :param folder_path:
    :return:
    """
    # Use cache
    if not os.path.exists("./_cache"):
        os.mkdir("./_cache")
    if os.path.exists("./_cache/label.bin"):
        with open("./_cache/label.bin", "rb") as f:
            print("Read labels from cache")
            return pickle.load(f)

    # Load from file
    label_folders = ["train", "test_a", "test_b", "val"]
    list_PA = []  # list: path,annotation
    for f in label_folders:
        set_folder = os.path.join(folder_path, f)  # (train test val) set
        # Check set folder existence
        if not os.path.exists(set_folder):
            raise FileNotFoundError("Folder " + f + " not found")
        # Extract image labels as: list [path, content]
        annotations = os.path.join(set_folder, "annotations.json")
        with open(annotations, "r") as file_ann:
            json_list = json.load(file_ann)  # json_list: annotation list
        for json_img in json_list:  # json_img: annotation for 1 image
            name = json_img["image_id"] + ".jpg"
            # Image full path
            full_path = os.path.join(set_folder, "images")
            full_path = os.path.join(full_path, name)
            # Check image existence
            if not os.path.exists(full_path):
                raise FileNotFoundError("Image " + full_path + " not found")
            list_PA.append((full_path, json_img))

    print("Read " + str(len(list_PA)) + " image labels.")
    with open("./_cache/label.bin", "wb+") as f:
        pickle.dump(list_PA, f)
    return list_PA

# load_aicha_to_list("/media/zc/Ext4-1TB/AI_challenger_keypoint")


def _pcm_1pt(x, y, width, height, variance):
    """
    Draw part confidence map of 1 point
    :param x:
    :param y:
    :param width:
    :param height:
    :param variance:
    :return: 2 dimensional image of shape [h,w]. values are heat value
    """
    one = np.ones([height, width], dtype=np.float32)
    # background: [h][w][2:xy]
    horizontal = np.arange(width)
    horizontal = horizontal[np.newaxis, :]  # h,w
    horizontal = horizontal * one
    vertical = np.arange(height)
    vertical = vertical[:, np.newaxis]  # h,w
    vertical = vertical * one
    hwc = np.stack([horizontal, vertical], axis=-1)  # hwc: h,w,c  c:xy

    # point: [h][w][xy]
    one = np.ones([height, width, 2])
    pt_hwc = np.array([x, y])
    pt_hwc = pt_hwc[np.newaxis, np.newaxis, :]
    pt_hwc = pt_hwc * one

    # norm
    distance_2 = hwc - pt_hwc  # 2: xy
    distance_2 = distance_2.astype(np.float32)
    norm = np.linalg.norm(distance_2, axis=2, keepdims=False)
    exp = np.exp(-(norm / 2.0 / variance / variance))
    return exp


def _paf_1pt(pA, pB, width, height, line_width):
    """
    Draw part affinity field of 1 vector. Return h,w,c
    :param pA: start of bone vector
    :param pB: end of bone vector
    :param width:
    :param height:
    :param line_width:
    :return: Heatmap with shape (h,w,c)
    """
    one = np.ones([height, width], dtype=np.float32)
    # background: [h][w][2:xy]
    horizontal = np.arange(width)
    horizontal = horizontal[np.newaxis, :]  # h,w
    horizontal = horizontal * one
    vertical = np.arange(height)
    vertical = vertical[:, np.newaxis]  # h,w
    vertical = vertical * one
    hwc = np.stack([horizontal, vertical], axis=-1)  # hwc: h,w,c  c:xy
    vAB = np.asarray(pB, np.float32) - np.asarray(pA, np.float32)  # 1 dimension: c. target line
    vAB = vAB[np.newaxis, :]
    vAB = vAB[np.newaxis, :]
    vAC = hwc - pA  # 3 dimension: h w c.

    # Perpendicular distance of C to AB
    # Cross Product : U x V = Ux * Vy - Uy * Vx
    cross_AB_AC = vAB[:,:,0] * vAC[:,:,1] - vAB[:,:,1] * vAC[:,:,0]
    norm_AB = np.linalg.norm(vAB, axis=2)
    dist_C_AB = cross_AB_AC / norm_AB

    # Projection length of C to AB
    # Dot Product: a dot b = axbx + ayby
    dot_AB_AC = vAB[:,:,0] * vAC[:,:,0] + vAB[:,:,1] * vAC[:,:,1]
    # a dot b = |a| |b| cos\theta
    proj_C_AB = dot_AB_AC / norm_AB

    mask_dist1 = np.ma.less_equal(dist_C_AB, line_width/2)  # distance less than +line_width
    mask_dist2 = np.ma.greater_equal(dist_C_AB, -line_width/2)  # distance more than - line_width
    mask_proj_1 = np.ma.less_equal(proj_C_AB, norm_AB)  # less than bone length
    mask_proj_2 = np.ma.greater_equal(proj_C_AB, 0.0)  # more than zero

    bone_proj = np.logical_and(mask_proj_1, mask_proj_2)
    mask_dist = np.logical_and(mask_dist1, mask_dist2)

    bone_mask = np.logical_and(bone_proj, mask_dist)

    vBone = vAB / norm_AB
    bone = bone_mask.astype(np.float32)
    bone = bone[..., np.newaxis]
    bone = vBone * bone  # h,w,c
    return bone


def _anno_resize(anno, resize_wh, resize_record):
    """
    Resize the x,y value in an annotation, in place.
    :param anno:
    :param resize_wh:
    :param resize_record:
    :return: None
    """
    w, h = resize_wh
    if "keypoint_annotations" not in anno:
        raise ValueError(str(anno) + " is not an image label from AI_Challenger dataset.")
    ks = anno["keypoint_annotations"]
    for k in ks.keys():  # k: One human
        # Resize x,y, leave "visible" alone
        p_xyv = ks[k]  # x, y, visible. vi=1可见，vi=2不可见，vi=3不在图内或不可推测
        p_xyv = np.asarray(p_xyv, dtype=np.int)
        p_xyv = p_xyv.reshape([14, 3])
        for j in range(14):
            xyv = p_xyv[j]
            nx, ny = bir.resize_pt(xyv[0:2], resize_record)
            xyv[0] = int(nx)
            xyv[1] = int(ny)
        p_xyv = np.reshape(p_xyv, [-1])
        p_xyv = list(p_xyv)
        ks[k] = p_xyv


def LI_load_resize(path_anno, resize_wh):
    """
    Load image, then resize image and annotations to network size
    :param path_anno:
    :param resize_wh:
    :return: resized_anno, resized_image
    """
    img_path, anno = path_anno
    w, h = resize_wh
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    r_img, resize_rec = bir.resize_img(img, (w, h))
    _anno_resize(anno, (w, h), resize_rec)  # resize happen in place
    return anno, r_img


def part_confidence_map(label, img_wh, zoom_times):
    """
    Use network size label to create part confidence map.
    :param label: network size label, not original one
    :param img_wh: network size
    :param zoom_times: wh/zoom = heat size
    :return: [joints, h, w]
    """
    img_w, img_h = img_wh
    # Check heat size divisible
    if img_w % zoom_times != 0 or img_h % zoom_times != 0:
        raise ValueError("network size (%d, %d) is not divisible by heat zoom_times (%d)." % (img_w, img_h, zoom_times))
    heat_w, heat_h = (img_w//zoom_times, img_h//zoom_times)
    if "keypoint_annotations" not in label:
        raise ValueError(str(label) + " is not an image label from AI_Challenger dataset.")
    ks = label["keypoint_annotations"]
    heat_pjhw = []
    for k in ks.keys():  # k: One human
        p_xyv = ks[k]  # x, y, visible. vi=1可见，vi=2不可见，vi=3不在图内或不可推测
        p_xyv = np.asarray(p_xyv, dtype=np.float32)
        p_xyv = p_xyv.reshape([14, 3])
        heat_jhw = []
        for j in range(14):  # each joint
            x,y,v = p_xyv[j]
            x,y = (x//zoom_times, y//zoom_times)
            if v != 3:
                heat = _pcm_1pt(x, y, heat_w, heat_h, 1.8)
            else:
                heat = np.zeros([heat_h, heat_w], dtype=np.float32)
            heat_jhw.append(heat)
        heat_jhw = np.stack(heat_jhw, axis=0)
        heat_pjhw.append(heat_jhw)
    heat_pjhw = np.stack(heat_pjhw, axis=0)
    heat_max_jhw = np.amax(heat_pjhw, axis=0)  # Sum each person's joint heatmap
    return heat_max_jhw


def part_affinity_field(label, img_wh, zoom_times):
    """
    Use network size label to create part affinity fields
    :param label:
    :param img_wh:
    :param zoom_times:
    :return: list of [p1b1, p1b2, p2b1, p2b2...] p: pair, b: bone.
    """
    img_w, img_h = img_wh
    # Check heat size divisible
    if img_w % zoom_times != 0 or img_h % zoom_times != 0:
        raise ValueError("network size (%d, %d) is not divisible by heat zoom_times (%d)." % (img_w, img_h, zoom_times))
    heat_w, heat_h = (img_w//zoom_times, img_h//zoom_times)
    if "keypoint_annotations" not in label:
        raise ValueError(str(label) + " is not an image label from AI_Challenger dataset.")
    ks = label["keypoint_annotations"]
    heat_pbhw = []
    for k in ks.keys():  # k: One human
        p_xyv = ks[k]  # x, y, visible. vi=1可见，vi=2不可见，vi=3不在图内或不可推测
        p_xyv = np.asarray(p_xyv, dtype=np.float32)
        p_xyv = p_xyv.reshape([14, 3])
        heat_bhw = []
        pairs = np.asarray([[1,2], [2,3], [4,5], [5,6], [7,8], [8,9], [10,11], [11,12], [13,14], [14,1], [14,4]]) - 1
        for pair in pairs[:]:  # each pair
            pA, pB = pair  # pA: index number, start of vector, pB: end of vector

            xA,yA,vA = p_xyv[pA]
            xB,yB,vB = p_xyv[pB]

            xA,yA = (xA//zoom_times, yA//zoom_times)
            xB,yB = (xB//zoom_times, yB//zoom_times)

            # Visibility check

            if vA != 3 and vB != 3:
                heat = _paf_1pt((xA, yA), (xB, yB), heat_h, heat_w, 2.5)
            else:
                heat = np.zeros([heat_h, heat_w, 2], dtype=np.float32)
            heat_bhw.append(heat[:,:,0])
            heat_bhw.append(heat[:,:,1])
        heat_bhw = np.stack(heat_bhw, axis=0)
        heat_pbhw.append(heat_bhw)
    heat_pbhw = np.stack(heat_pbhw, axis=0)
    heat_max_bhw = np.amax(heat_pbhw, axis=0)  # Sum each person's joint heatmap
    return heat_max_bhw


def generator_BH_BI(batch_size, img_size):
    """
    Generate Batch Heatmap - Batch Image pair
    Batch Heatmap shape: [B,H,W,C] C: 14(pcm) + 11*2(paf)
    Batch Image shape: [B,H,W,C] C: 3 channels
    :param batch_size:
    :return:
    """
    annotations = load_aicha("/media/zc/Ext4-1TB/AI_challenger_keypoint")
    random.shuffle(annotations)
    for i in range(0, len(annotations)-batch_size, batch_size):
        batch_anno = annotations[i: i+batch_size]
        LIs = [LI_load_resize(anno, img_size) for anno in batch_anno]
