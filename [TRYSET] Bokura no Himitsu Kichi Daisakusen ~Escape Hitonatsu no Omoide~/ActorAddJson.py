import argparse
import json
import os
import re


def load_name_map(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize_name(name):
    if not isinstance(name, str):
        return None
    trimmed = name.strip()
    return trimmed if trimmed else None


def map_actor_name(name, name_map):
    if not isinstance(name, str):
        return None

    # Keep original spacing (including full-width spaces) in output.
    if name in name_map:
        return name_map[name]

    stripped = name.strip()
    if not stripped:
        return None

    # Fallback for map files that store trimmed keys.
    if stripped in name_map:
        return name_map[stripped]

    return name


def row_starts_with_actor(row, actor_name):
    if not actor_name or not isinstance(row, list) or not row:
        return False
    return normalize_name(row[0]) == actor_name


def actor_from_data_row(row, name_map):
    if not isinstance(row, list) or not row:
        return None
    candidate = row[0]
    if not isinstance(candidate, str) or not candidate.strip():
        return None
    if candidate in name_map or candidate.strip() in name_map:
        return map_actor_name(candidate, name_map)
    return None


def get_actor_from_parameters(row_parameters):
    if not isinstance(row_parameters, list):
        return None
    for entry in row_parameters:
        if isinstance(entry, dict):
            actor = normalize_name(entry.get('rowInfoText'))
            if actor:
                return actor
    return None


def process_file(file_key, file_data, name_map):
    data = file_data.get('data') or []
    parameters = file_data.get('parameters') or []
    context = file_data.get('context') or []
    tags = file_data.get('tags') or []

    new_data = []
    new_context = []
    new_tags = []
    new_parameters = []
    inserted_rows = 0
    current_speaker = None

    for i, row in enumerate(data):
        actor_name = None
        if i < len(parameters):
            actor_name = get_actor_from_parameters(parameters[i])

        mapped_actor = map_actor_name(actor_name, name_map)
        previous_output_row = new_data[-1] if new_data else None
        if (
            mapped_actor
            and mapped_actor != current_speaker
            and not row_starts_with_actor(previous_output_row, mapped_actor)
        ):
            new_data.append([mapped_actor, '', '', '', ''])
            new_context.append([])
            new_tags.append([])
            new_parameters.append([])
            inserted_rows += 1
            current_speaker = mapped_actor

        if mapped_actor:
            current_speaker = mapped_actor

        new_data.append(row)
        new_context.append(context[i] if i < len(context) else [])
        new_tags.append(tags[i] if i < len(tags) else [])
        new_parameters.append(parameters[i] if i < len(parameters) else [])

        # Keep speaker state aligned when original data row already contains a known actor name.
        source_row_actor = actor_from_data_row(row, name_map)
        if source_row_actor:
            current_speaker = source_row_actor

    file_data['data'] = new_data
    file_data['context'] = new_context
    file_data['tags'] = new_tags
    file_data['parameters'] = new_parameters
    print(f"Processed {file_key}: +{inserted_rows} actor rows")


def is_target_scenario_file(file_key):
    return bool(re.match(r'^/data/scenario/.+\.ks$', file_key))


def main():
    parser = argparse.ArgumentParser(
        description='Insert actor rows based on rowInfoText into Translator++ project files.'
    )
    parser.add_argument('--input', default='TRYSET.trans', help='Input project JSON file')
    parser.add_argument('--output', default='modified_autosave.json', help='Output JSON file')
    parser.add_argument('--name-map', default='name_map.json', help='Optional actor name map JSON file')
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        project = json.load(f)

    name_map = load_name_map(args.name_map)
    files = project.get('project', {}).get('files', {})

    if not files:
        raise ValueError('No project files found under project.files')

    processed_count = 0
    for file_key, file_data in files.items():
        if not is_target_scenario_file(file_key):
            continue
        process_file(file_key, file_data, name_map)
        processed_count += 1

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(project, f, ensure_ascii=False, indent=2)

    print(f"Done. Processed {processed_count} scenario files.")
    print(f"Saved modified project as: {args.output}")


if __name__ == '__main__':
    main()