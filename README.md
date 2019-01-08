# lc3as
lc3 assembler

## features

- [x] all syntax supported by lc3edit

- [x] label expression (inspired by [lc3tools](https://github.com/haplesshero13/lc3tools))(not supported by lc3edit)  
  So if you have a label like `this_is_a_label`，`.FILL this_is_a_label+#30` is a legal expression

  Note: in lc3edit, if you have a label named `x`, and there is an instruction `.FILL x+5`，lc3edit will view it as an immediate.  But lc3as will treat it as a label expression if there is a label named x.

- [x] multiple labels (not supported by lc3edit)

## Usage

To assemble lc3 asm file:

```shell
python lc3as.py infile -o outfile
```

For more help:

```
python lc3as.py -h
```