# print the header (the first line of input)
# and then run the specified command on the rest of the input
IFS= read -r header
printf '%s\n' "$header"
"$@"
