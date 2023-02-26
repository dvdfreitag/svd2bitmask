# svd2bitmask

Generates bitmask style headers for embedded devices using SVD files in the style which some Atmel devices use

## Usage

```
$ ./svd2bitmask.py -h
usage: svd2bitmask.py [-h] [-v] [-f FILE] [-o OUTPUT] [-c] [-p PREFIX]

options:
  -h, --help            show this help message and exit
  -v, --verbose         Output extra information when parsing
  -f FILE, --file FILE  Input SVD file to parse
  -o OUTPUT, --output OUTPUT
                        Output directory for header files
  -c, --create          Create Output directory if it does not exist
  -p PREFIX, --prefix PREFIX
                        Output header file prefix (<prefix>_<peripheral name>.h>
```

- Verbosity: Passing one or more verbose flags will increase verbosity, eg `-vvv`
- File: Input SVD file to read
- Output: Directory to create header files in. If you do not pass the output flag, `svd2bitmask` will do a dry run without generating any header files
- Create: Instructs `svd2bitmask` to create the supplied output directory if it does not already exist
- Prefix: By default, `svd2bitmask` will use the device name present in the SVD file. Supplying a prefix will override this value. The prefix is used to generate the header files.

Example:
```
./svd2bitmask.py -f ./svd/WCH/RISC-V/CH32V307/NoneOS/CH32V307xx.svd -o test -c -p ch32v30x
```

Run `svd2bitmask` using `CH32V307xx.svd` as the input file, then write the resulting headers to `./test`, creating the output directory if needed. Since `prefix` is passed, the headers will be named `ch32v30x_<peripheral name>.h`

## Duplicates

A duplicate peripheral is considered by `svd2bitmask` as a peripheral which is defined in an SVD file that has the same naming convention as more than one unique peripheral that is not also derived. Where the naming convention might be `ADC1`, `ADC2`, etc. 

If `svd2bitmask` finds any duplicate peripherals, it will create a `duplicate` directory where the duplicate peripheral headers will be written. In addition, `svd2bitmask` will also generate a diff file between the original peripheral and the duplicate to facilitate implementation of the generated library.

## Two Step Process

The process of writing such a bitmask or bit field based library is largely consumed with the extremely tedious task of transcribing registers from a datasheet or known-good library. `svd2bitmask` exists to automate this process, however the output of `svd2bitmask` should never be used directly.

Once `svd2bitmask` has been run, it is imperative that you verify each peripheral against the datasheet or a known-good library. It's important to do this since an SVD file can contain erroneous data.

## Unions

Each register is defined as a union of an anonymous struct containing bit fields which correspond to the register's fields:

```C
/******************** ADC Status Register ********************/
typedef union
{
	struct
	{
		uint32_t AWD: 1;	// Bit 0: Analog Watchdog
		uint32_t EOC: 1;	// Bit 1: End of Conversion
		uint32_t JEOC: 1;	// Bit 2: Injected Channel Group End of Conversion
		uint32_t JSTRT: 1;	// Bit 3: Injected Channel Group Conversion Sart
		uint32_t STRT: 1;	// Bit 4: Start of Conversion
		uint32_t: 27;		// Bit 5-31: Reserved
	} bit;
	uint32_t reg;
} ADC_STATR_t;

#define ADC_STATR_RESETVALUE	((uint32_t)0x00)
#define ADC_STATR_MASK		((uint32_t)0x1F)

#define ADC_STATR_AWD_Pos	((uint32_t)0)
#define ADC_STATR_AWD		((uint32_t)(1 << ADC_STATR_AWD_Pos))
#define ADC_STATR_EOC_Pos	((uint32_t)1)
#define ADC_STATR_EOC		((uint32_t)(1 << ADC_STATR_EOC_Pos))
#define ADC_STATR_JEOC_Pos	((uint32_t)2)
#define ADC_STATR_JEOC		((uint32_t)(1 << ADC_STATR_JEOC_Pos))
#define ADC_STATR_JSTRT_Pos	((uint32_t)3)
#define ADC_STATR_JSTRT		((uint32_t)(1 << ADC_STATR_JSTRT_Pos))
#define ADC_STATR_STRT_Pos	((uint32_t)4)
#define ADC_STATR_STRT		((uint32_t)(1 << ADC_STATR_STRT_Pos))
```

## Peripheral Definition

Once all of the registers have been added, a struct for each peripheral is generated which contains all of the registers. In addition to the bit field unions, a struct using built-in types is also generated. The bit field peripheral struct is enabled by defining `BITMASK`:

```C
/******************** Analog to Digital Converter ********************/
#ifdef BITMASK
	typedef struct
	{
		volatile ADC_STATR_t STATR;		// Status Register
		volatile ADC_CTLR1_t CTLR1;		// Control 1
		volatile ADC_CTLR2_t CTLR2;		// Control 2
		volatile ADC_SAMPTR1_t SAMPTR1;		// Sample Time Configuration 1
		volatile ADC_SAMPTR2_t SAMPTR2;		// Sample Time Configuration 2
		volatile ADC_IOFR_t IOFR[4];		// Injected Channel Data Offset
		volatile ADC_WDHTR_t WDHTR;		// Watchdog High Threshold
		volatile ADC_WDLTR_t WDLTR;		// Watchdog Low Threshold
		volatile ADC_RSQR1_t RSQR1;		// Regular Channel Sequence 1
		volatile ADC_RSQR2_t RSQR2;		// Regular Channel Sequence 2
		volatile ADC_RSQR3_t RSQR3;		// Regular Channel Sequence 3
		volatile ADC_ISQR_t ISQR;		// Injected Channel Sequence
		volatile ADC_IDATAR_t IDATAR1[4];	// Injected Data
		volatile ADC_RDATAR_t RDATAR;		// Regular Data
	} ADC_t;
#else
	typedef struct
	{
		volatile uint32_t STATR;	// Status Register
		volatile uint32_t CTLR1;	// Control 1
		volatile uint32_t CTLR2;	// Control 2
		volatile uint32_t SAMPTR1;	// Sample Time Configuration 1
		volatile uint32_t SAMPTR2;	// Sample Time Configuration 2
		volatile uint32_t IOFR1;	// Injected Channel Data Offset 1
		volatile uint32_t IOFR2;	// Injected Channel Data Offset 2
		volatile uint32_t IOFR3;	// Injected Channel Data Offset 3
		volatile uint32_t IOFR4;	// Injected Channel Data Offset 4
		volatile uint32_t WDHTR;	// Watchdog High Threshold
		volatile uint32_t WDLTR;	// Watchdog Low Threshold
		volatile uint32_t RSQR1;	// Regular Channel Sequence 1
		volatile uint32_t RSQR2;	// Regular Channel Sequence 2
		volatile uint32_t RSQR3;	// Regular Channel Sequence 3
		volatile uint32_t ISQR;		// Injected Channel Sequence
		volatile uint32_t IDATAR1;	// Injected Data 1
		volatile uint32_t IDATAR2;	// Injected Data 2
		volatile uint32_t IDATAR3;	// Injected Data 3
		volatile uint32_t IDATAR4;	// Injected Data 4
		volatile uint32_t RDATAR;	// Regular Data
	} ADC_t;
#endif
```

## Header usage

With `BITMASK` defined, if you want to write a specific bit:

```C
// Enable ADC Analog Watchdog
ADC.STATR.bit.AWD = 1;

// Or,
ADC.STATR.reg |= ADC_STATR_AWD;
```

Without `BITMASK` defined, if you want to write a specific bit:

```C
// Enable ADC Analog Watchdog
ADC.STATR |= ADC_STATR_AWD;
```

The `BITMASK` check exists for anyone who does not care for the union style bit field registers but still wishes to use the generated library.

