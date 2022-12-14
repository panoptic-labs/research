# @author Axicon Labs Inc.
echo "🟡 activating..."
python3 -m venv panoptic-research
source panoptic-research/bin/activate

panoptic-research/bin/pip install --upgrade pip
panoptic-research/bin/pip install -r requirements.txt
echo "🟢 virtual environment activated"
