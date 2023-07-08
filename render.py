import os
import time
import numpy as np
import mitsuba as mi
import simple3d
from utils import standardize_bbox, generate_pos_colormap, get_xml, fps


def render(config, data):
    file_name = config.path.split('.')[0]
    pcl = data[:, [2, 0, 1]]
    pcl[:, 0] *= 1
    pcl[:, 2] += 0.0125

    if config.knn:
        knn_center = fps(pcl, config.center_num)
        knn_center += 0.5
        knn_center[:, 2] -= 0.0125
    else:
        knn_center = []
    
    if config.mask:
        mask_center = fps(pcl, 128)
        mask_center = mask_center[:64]

    xml_head, xml_object_segment, xml_tail = get_xml(config.res, config.view, config.radius, config.type)
    xml_segments = [xml_head]

    x, y, z = float(config.translate[0]), float(config.translate[1]), float(config.translate[2])
    scale_x, scale_y, scale_z = float(config.scale[0]), float(config.scale[1]), float(config.scale[2])

    with_color = True if data.shape[1] == 6 else False
    for i in range(pcl.shape[0]):
        if config.mask:
            mask = False
            for j in range(len(mask_center)):
                if distance(pcl[i], mask_center[j]) < 0.05:
                    mask = True
                    break
            if mask:
                continue
        if config.white:
            color = [0.6, 0.6, 0.6]
        elif config.RGB != []:
            color = [int(i) / 255 for i in config.RGB]
        elif with_color:
            color = [data[i, 3], data[i, 4], data[i, 5]]
        else:
            # rander the point with position generate_pos_colormap
            color = generate_pos_colormap(pcl[i, 0] + 0.5, pcl[i, 1] + 0.5, pcl[i, 2] + 0.5 - 0.0125,
                                            config, knn_center)
        xml_segments.append(xml_object_segment.format(
            (pcl[i, 0] + x) * scale_x, (pcl[i, 1] + y) * scale_y, (pcl[i, 2] + z) * scale_z, *color))

    xml_segments.append(xml_tail)
    xml_content = str.join('', xml_segments)

    os.makedirs(config.workdir, exist_ok=True)
    xmlFile = f'{config.workdir}/{file_name}.xml'
    with open(xmlFile, 'w') as f:
        f.write(xml_content)
    f.close()

    mi.set_variant("scalar_rgb")
    scene = mi.load_file(xmlFile)
    image = mi.render(scene, spp=256)
    mi.util.write_bitmap(config.output, image)
    # To prevent errors in the output image, we delay some seconds
    time.sleep(int(config.res[0]) / 1000)
    os.remove(xmlFile)


def render_part(config, pcl):
    file_name = config.path.split('.')[0]
    pcl = pcl[:, [2, 0, 1]]
    pcl[:, 0] *= -1
    pcl[:, 2] += 0.0125

    knn_center = fps(pcl, config.center_num)
    knn_center += 0.5
    knn_center[:, 2] -= 0.0125

    # config.res[0] /= 2
    # config.res[1] /= 2
    config.radius *= 2

    pcl_list = [[] for i in range(config.center_num)]
    for i in range(pcl.shape[0]):
        x, y, z = pcl[i, 0] + 0.5, pcl[i, 1] + 0.5, pcl[i, 2] + 0.5 - 0.0125
        temp = abs(knn_center[:, 0] - x) + abs(knn_center[:, 1] - y) + abs(knn_center[:, 2] - z)
        index = np.argmin(temp)
        pcl_list[index].append(pcl[i])

    for i in range(config.center_num):
        knn_patch = np.array(pcl_list[i])
        xml_head, xml_object_segment, xml_tail = get_xml(config.res, config.view, config.radius, config.type)
        xml_segments = [xml_head]

        knn_patch = standardize_bbox(knn_patch)
        for j in range(len(knn_patch)):
            color = generate_pos_colormap(knn_patch[j, 0] + 0.5, knn_patch[j, 1] + 0.5, knn_patch[j, 2] + 0.5 - 0.0125, config, [])
            xml_segments.append(xml_object_segment.format(knn_patch[j, 0], knn_patch[j, 1], knn_patch[j, 2], *color))

        xml_segments.append(xml_tail)
        xml_content = str.join('', xml_segments)

        os.makedirs(config.workdir, exist_ok=True)
        xmlFile = f'{config.workdir}/{file_name}.xml'
        with open(xmlFile, 'w') as f:
            f.write(xml_content)
        f.close()

        mi.set_variant("scalar_rgb")
        scene = mi.load_file(xmlFile)
        image = mi.render(scene, spp=256)

        output_file = config.output.split('.')[0] + f'_{str(i)}.' + config.output.split('.')[1]
        mi.util.write_bitmap(output_file, image)
        # To prevent errors in the output image, we delay some seconds
        time.sleep(int(config.res[0]) / 1000)
        os.remove(xmlFile)


def distance(p1, p2):
    return np.sqrt(np.sum(np.square(p1 - p2)))


def real_time_tool(config, pcl):
    simple3d.showpoints(pcl, config)
