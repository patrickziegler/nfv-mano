import yaml
import json

with open("nsd.yaml", 'r') as fp:
    try:
        data = yaml.safe_load(fp)
        print(json.dumps(data, indent=4))
    except yaml.YAMLError as exc:
        print(exc)
