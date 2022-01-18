#!/bin/bash
set -e

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
  echo -n "What tool do you want to install? "
  read -r TOOL_PACKAGE
  if [[ $TOOL_PACKAGE =~ ^[a-z]+$ ]]; then
    break
  else
    echo "Invalid tool name"
  fi
done

while true; do
  echo -n "What version of $TOOL_PACKAGE do you want to install? "
  read -r NPM_VERSION
  if [[ $NPM_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    break
  else
    echo "Invalid version number"
  fi
done

{
  echo "#!/bin/bash"
  echo ""
  echo ". .ntw.sh"
  echo ""
  echo "selectNode v${NODE_VERSION}"
  echo "selectTool ${TOOL_PACKAGE} ${NPM_VERSION}"
  echo ""
  echo "${TOOL_PACKAGE} \$@"
} > "${TOOL_PACKAGE}w"
chmod +x "${TOOL_PACKAGE}w"

curl -sL https://raw.githubusercontent.com/rahulsom/node-tool-wrapper/main/.ntw.sh > .ntw.sh
