import os
import re
from collections import defaultdict

from dotenv import load_dotenv
from tqdm import tqdm

import supervisely as sly

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

api = sly.Api()
workspace_id = sly.env.workspace_id()
TAG_NAME = "car"

# OPTION 1: upload images, add tags and enable images grouping by tag values
ALL_IMAGES_DIR = "./cars catalog/all_images"

project_name = os.path.basename(os.path.normpath(ALL_IMAGES_DIR))
project = api.project.create(workspace_id, project_name, change_name_if_conflict=True)
dataset = api.dataset.create(project.id, "ds0")


# create tag meta with type "any string"
tag_meta = sly.TagMeta(TAG_NAME, sly.TagValueType.ANY_STRING)

project_meta = sly.ProjectMeta()  # new project meta (because we have just created new project)
project_meta = project_meta.add_tag_meta(new_tag_meta=tag_meta)
api.project.update_meta(id=project.id, meta=project_meta)


images_paths = sly.fs.list_files(ALL_IMAGES_DIR, valid_extensions=sly.image.SUPPORTED_IMG_EXTS)
images_names = [os.path.basename(img_path) for img_path in images_paths]

# upload images to Supervisely
progress = tqdm(images_paths, desc="Upload images", total=len(images_paths))
images_infos = api.image.upload_paths(
    dataset.id, images_names, images_paths, progress_cb=progress.update
)


project_meta_from_server = sly.ProjectMeta.from_json(api.project.get_meta(project.id))

tag_meta = project_meta_from_server.get_tag_meta(TAG_NAME)


tag2images_mapping = defaultdict(list)
for image_info in images_infos:
    # we will use regexp to get tag value from image name (e.g. "aston_martin_1.jpg" -> "aston_martin")
    # it is just an example, you can use any other logic for your case
    image_name = sly.fs.get_file_name(image_info.name)
    tag_value = re.match(r"(.+?)_\d+", image_name).group(1)
    tag2images_mapping[tag_value].append(image_info.id)

# batch add tags to images on server
for tag_value, images_ids in tag2images_mapping.items():
    api.image.add_tag_batch(images_ids, tag_meta.sly_id, value=tag_value)

# enable images grouping by "car" tag values
api.project.images_grouping(project.id, enable=True, tag_name=TAG_NAME)


# ======================================================================================
# ======================================================================================
# ======================================================================================

# OPTION 2: upload images as a group
SPLITTED_IMAGES_DIR = "./cars catalog/splitted_images"

# create project and dataset
project_name = os.path.basename(os.path.normpath(SPLITTED_IMAGES_DIR))
project = api.project.create(workspace_id, project_name, change_name_if_conflict=True)
dataset = api.dataset.create(project.id, "ds0")

# create tag meta with type "any string" and update project meta on server
project_meta = sly.ProjectMeta()  # empty project meta (because we have just created new project)
tag_meta = sly.TagMeta(TAG_NAME, sly.TagValueType.ANY_STRING)
project_meta = project_meta.add_tag_meta(new_tag_meta=tag_meta)
api.project.update_meta(id=project.id, meta=project_meta)

# easily upload images as a groups to Supervisely
for group_name in os.listdir(SPLITTED_IMAGES_DIR):
    group_dir = os.path.join(SPLITTED_IMAGES_DIR, group_name)
    if not os.path.isdir(group_dir):
        continue
    images_paths = sly.fs.list_files(group_dir, valid_extensions=sly.image.SUPPORTED_IMG_EXTS)

    api.image.upload_grouped_images(dataset.id, tag_meta.name, group_name, images_paths)

api.project.images_grouping(project.id, enable=True, tag_name=TAG_NAME)
