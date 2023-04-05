
To run:

```
poetry install
poetry shell

invoke build
invoke deploy
# Or just: `invoke all`
```

This assumes that the applications are in a subfolder `nua-apps` of the current folder.

For instance, that there is a symblink from the `real-apps` folder of the `nua` sources to `./nua-apps`.

You may also set the following env vars (or set a local `.env` file):

- `NUA_DOMAIN`: domain (e.g.: apps.my-domain.com)
- `NUA_HOST`: host where the orchestrator is running
- `NUA_APPS_ROOT`: the folder where the apps are located, if it's not `./nua-apps`.
