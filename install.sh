#!/bin/bash
set -e

# Fetch the latest Node.js versions and suggest LTS
echo "Fetching Node.js version information..."
LATEST_VERSIONS=$(curl -s https://nodejs.org/dist/index.json | jq -r '.[].version' | sed 's/^v//' | sort -V | awk -F. '{print $1 "." $2 "." $3}' | awk -F. '{versions[$1] = $0} END {for (major in versions) print versions[major]}' | sort -nr | head -4 | sort -n)
LATEST_LTS=$(curl -s https://nodejs.org/dist/index.json | jq -r '.[] | select(.lts != false) | .version' | head -1 | sed 's/^v//')

echo "Latest versions by major release:"
echo "$LATEST_VERSIONS" | xargs echo | sed -e 's/ /            /g'
echo ""
if [[ -n "$LATEST_LTS" ]]; then
  echo "Suggested Node.js version (Latest LTS): $LATEST_LTS"
fi

while true; do
  echo -n "What version of nodejs do you want to install? "
  read -r NODE_VERSION
  if [[ $NODE_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    break
  else
    echo "Invalid version number"
  fi
done

while true; do
  echo "Tool Examples: npm, yarn, pnpm, node"
  echo -n "What tool do you want to install? "
  read -r TOOL_PACKAGE
  if [[ $TOOL_PACKAGE =~ ^[a-z]+$ ]]; then
    break
  else
    echo "Invalid tool name"
  fi
done

if [[ $TOOL_PACKAGE != "node" ]]; then
  while true; do
    echo -n "What version of $TOOL_PACKAGE do you want to install? "
    read -r TOOL_VERSION
    if [[ $TOOL_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      break
    else
      echo "Invalid version number"
    fi
  done
fi

{
  echo "#!/bin/bash"
  echo ""
  echo ". .ntw.sh"
  echo ""
  echo "selectNode v${NODE_VERSION}"
  if [[ $TOOL_PACKAGE != "node" ]]; then
    echo "selectTool ${TOOL_PACKAGE} ${TOOL_VERSION}"
  fi
  echo ""
  echo "${TOOL_PACKAGE} \"\$@\""
} > "${TOOL_PACKAGE}w"
chmod +x "${TOOL_PACKAGE}w"

curl -sL https://raw.githubusercontent.com/rahulsom/node-tool-wrapper/main/.ntw.sh > .ntw.sh
chmod +x .ntw.sh
