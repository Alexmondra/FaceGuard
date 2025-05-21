# FaceGuard - Sistema de Reconocimiento Facial con Python y OpenCV

usar python version 3.10.13 =>version estable

# Caso de usar virtualenv
python3 -m venv face      => crear ambiente virtual
source face/bin/activate  => activar el ambiente virtual
pip install -r requirements.txt
deactivate                 => desactivar ambiente virtual

# Caso de usar pyenv

pyenv virtualenv 3.10.13 face310 => crear ambiente virtual
pyenv activate face310           => activar ambiente virtual
pip install -r requirements.txt
pyenv deactivate                 => desactivar ambiente virtual
pyenv uninstall face310          => eliminar ambiente 