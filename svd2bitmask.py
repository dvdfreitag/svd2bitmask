#!/usr/bin/env python
import argparse
import os
import xml.etree.ElementTree as ET
import re
import difflib

class Peripheral:
	def __init__(self, realname, description, registers):
		m = re.match(r'(\w+)\d+$', realname)

		if m is not None:
			self.name = m[1]
		else:
			self.name = realname

		self.realname = realname
		self.description = description
		self.registers = registers
		self.path = ''

	def __lt__(self, other):
		return self.name < other.name

	def __eq__(self, other):
		if self.name != other.name:
			return False

		if self.description != other.description:
			return False

		if len(self.registers) != len(other.registers):
			return False

		for i in range(len(self.registers)):
			if self.registers[i] != other.registers[i]:
				return False

		return True

	def register_count(self):
		count = 0

		for register in self.registers:
			count += 1

		return count

	def field_count(self):
		count = 0

		for register in self.registers:
			for field in register.fields:
				count += 1

		return count

class Register:
	def __init__(self, size, offset, name='', description='', type='UNKNOWN', fields=[], reserved=False, reset=0):
		self.size = size
		self.offset = offset
		self.name = name
		self.description = description
		self.type = type
		self.fields = fields
		self.reserved = reserved
		self.reset = reset

	def __lt__(self, other):
		return self.offset < other.offset

	def __eq__(self, other):
		if self.size != other.size:
			return False

		if self.offset != other.offset:
			return False

		if self.name != other.name:
			return False

		if self.description != other.description:
			return False

		if self.type != other.type:
			return False

		if len(self.fields) != len(other.fields):
			return False

		for i in range(len(self.fields)):
			if self.fields[i] != other.fields[i]:
				return False

		if self.reserved != other.reserved:
			return False

		if self.reset != other.reset:
			return False

		return True

class Field:
	def __init__(self, name, description, offset, width, readonly):
		self.name = name
		self.description = description
		self.offset = offset
		self.width = width
		self.readonly = readonly

	def __lt__(self, other):
		return self.offset < other.offset

	def __eq__(self, other):
		if self.name != other.name:
			return False

		if self.description != other.description:
			return False

		if self.offset != other.offset:
			return False

		if self.width != other.width:
			return False

		if self.readonly != other.readonly:
			return False

		return True

def strip_text(text):
	# Strip any newlines or excess whitespace from supplied text
	output = ""

	# Split on newlines
	lines = text.splitlines()

	# If there are any newlines present,
	if (len(lines)) > 1:
		# For each line,
		for line in lines:
			# Strip excess whitespace,
			#   replace the newline with a space,
			#   and append to output
			output += line.strip() + ' '
	else:
		# Otherwise, strip the text and return it
		return text.strip()

	# Finally, return the stripped output
	return output.strip()

def get_xml_text(name, xml, default='', fullStrip=True):
	text_xml = xml.find(name)

	if text_xml is None:
		return default

	if text_xml.text is None:
		return default

	if fullStrip == True:
		return strip_text(text_xml.text)
	else:
		return text_xml.text.strip()

def print_registers(peripheral, verbose=0):
	output = []

	# Output a C bitmask union of the following style:
	# typedef union
	# {
	# 	struct
	# 	{
	# 		<type> <Field Name>: <Field Size>;	// Bit <Field Bits>: <Field Description>
	# 		<type>: <Reserved Bits Size>;	// Bit <Field Bits>: Reserved
	# 	} bit;
	# 	<type> reg;
	# } <Peripheral Name>_<Register Name>_t;

	# For all Registers in the Peripheral,
	for register in peripheral.registers:
		# Some registers have no fields
		if len(register.fields) < 1:
			continue

		union = f'// ---------- {peripheral.description} {register.description} ----------\n'
		union += 'typedef union\n{\n\tstruct\n\t{\n'

		field_names = []

		# ... and all Fields in each Register,
		for field in register.fields:
			union += '\t\t'

			# If the field is readonly, append const keyword
			if field.readonly == True:
				union += 'const '

			# Compute the length of the field
			start = field.offset
			end = field.offset + field.width - 1

			# If start = end, the field is 1 bit
			if start == end:
				# Single bit formatting: Bit <N>
				position = f'Bit {start}'
			else:
				# Multi-bit formatting: Bits <N>-<M>
				position = f'Bits {start}-{end}'

			union += register.type

			# Reserved fields will not contain a name
			if len(field.name) > 0:
				union += f' {field.name}'
				field_names.append(field.name)

			# Format each field: [const] <Type> <Field Name>: <Field Size>\t// <Field Bit Size>: <Field Description>
			union += f': {field.width};\t// {position}: {field.description}\n'

		# Format union name: <Peripheral Name>_<Register Name>_t
		union += f'\t}} bit;\n\t{register.type} reg;\n}} {peripheral.name}_{register.name}_t;\n\n'

		union += f'#define {peripheral.name}_{register.name}_RESETVALUE\t(({register.type})0x{register.reset:X})\n'

		# Filter out any reserved fields
		filtered = list(filter(lambda register: len(register.name) > 0, register.fields))

		mask = 0
		for field in filtered:
			for i in range(field.width):
				mask |= (1 << (i + field.offset))

		union += f'#define {peripheral.name}_{register.name}_Mask\t(({register.type})0x{mask:X})\n\n'

		for field in filtered:
			union += f'#define {peripheral.name}_{register.name}_{field.name}_Pos\t(({register.type}){field.offset})\n'

			if field.width == 1:
				# Format bit mask defines: #define <Peripheral Name>_<Register Name>_<Field Name>\t((<Register Size>)<value>)
				union += f'#define {peripheral.name}_{register.name}_{field.name}\t(({register.type})(1 << {peripheral.name}_{register.name}_{field.name}_Pos))\n'

				if field != filtered[-1]:
					union += '\n'
			else:
				mask = 0
				for i in range(field.width):
					mask |= (1 << (i + field.offset))

				union += f'#define {peripheral.name}_{register.name}_{field.name}_Msk\t(({register.type})(0x{mask:X} << {peripheral.name}_{register.name}_{field.name}_Pos))\n'
				union += f'#define {peripheral.name}_{register.name}_{field.name}_Val(v)\t(({register.type})(((v) & {peripheral.name}_{register.name}_{field.name}_Msk) >> {peripheral.name}_{register.name}_{field.name}_Pos))\n'
				union += f'#define {peripheral.name}_{register.name}_{field.name}(v)\t(({register.type})(((v) << {peripheral.name}_{register.name}_{field.name}_Pos) & {peripheral.name}_{register.name}_{field.name}_Msk)\n'

		if verbose > 2:
			print(union)

		# Append formatted Register union to output array
		output.append(union)

	# Return array of formatted unions for all Registers in the supplied Peripheral
	return output

def print_peripheral(peripheral, verbose=0):
	# Output a set of C structs with the following format:
	# #ifdef BITMASK
	# 	typedef struct
	# 	{
	# 		volatile <Field Type> <Field Name>;	// <Field Description>
	# 		uint32_t: <Reserved Size>;	// Reserved
	# 	} <Peripheral Name>_t;
	# #else
	# 	typedef struct
	# 	{
	# 		volatile <type> <Field Name>;	// <Field Description>
	# 		uint32_t: <Reserved Size>;	// Reserved
	# 	} <Peripheral Name>_t;
	# #endif

	struct = '#ifdef BITMASK\n'
	struct += '\ttypedef struct\n\t{\n'

	for register in peripheral.registers:
		if register.reserved == True:
			# Format reserved registers: const volatile uint32_t: <size>;	// Reserved
			struct += f'\t\tconst volatile uint32_t: {register.size};\t// Reserved\n'

		# If a specified register has fields,
		elif len(register.fields) > 0:
			# Format each register using Bitmask Unions: volatile <Field Type> <Field Name>;	// <Field Description>
			struct += f'\t\tvolatile {peripheral.name}_{register.name}_t {register.name};\t// {register.description}\n'
		else:
			# Otherwise, format each register using built-in type: volatile <type> <Field Name>;	// <Field Description>
			struct += f'\t\tvolatile {register.type} {register.name};\t// {register.description}\n'

	struct += f'\t}} {peripheral.name}_t;\n'
	struct += '#else\n'
	struct += '\ttypedef struct\n\t{\n'

	for register in peripheral.registers:
		if register.reserved == True:
			# Format reserved registers: const volatile uint32_t: <size>;	// Reserved
			struct += f'\t\tconst volatile uint32_t: {register.size};\t// Reserved\n'
		else:
			# Format each register using built-in type: volatile <type> <Field Name>;	// <Field Description>
			struct += f'\t\tvolatile {register.type} {register.name};\t// {register.description}\n'

	# Format Struct name: <Peripheral Name>_t
	struct += f'\t}} {peripheral.name}_t;\n'
	struct += '#endif'

	if verbose > 2:
		print(struct)

	return struct

def load_peripheral(peripheral, verbose=0):
	name_xml = get_xml_text('name', peripheral)
	description_xml = get_xml_text('description', peripheral)

	registers_xml = peripheral.find('registers')
	registers = load_registers(name_xml, registers_xml, verbose)

	# Failed to parse register map, exit
	if not registers:
		return None

	# Ensure Registers are sorted by offset
	registers.sort()

	if len(registers) > 0 and registers[0].offset != 0:
		start_next = registers[0].offset

		# Add a reserved section from bit 0 to the start of the next Register
		registers.insert(0, Register(0, start_next - 1, reserved=True))

		if verbose > 1:
			print(f'  └> {name_xml}: Reserved section added at offset 0: {start_next - 1}')

	for i in range(len(registers) - 1):
		start = registers[i].offset
		end = start + registers[i].size

		start_next = registers[i + 1].offset
		diff = start_next - end

		# If there is a gap, add a Reserved section
		if diff > 0:
			registers.append(Register(diff, end, reserved=True))

			if verbose > 1:
				print(f'  └> {name_xml}: Reserved section added at offset {diff}: {end}')

	# Re-sort after adding necessary reserved sections
	registers.sort()

	return Peripheral(name_xml, description_xml, registers)

def load_registers(peripheral_name, registers, verbose=0):
	# Array of Register objects
	output = []

	for register in registers:
		# Array of field objects
		fields = []

		name_xml = get_xml_text('name', register)
		description_xml = get_xml_text('description', register)
		size_xml = int(get_xml_text('size', register), 16)
		offset_xml = int(get_xml_text('addressOffset', register), 16)
		reset_xml = get_xml_text('resetValue', register)

		# Check to see if a register has a reset value
		if reset_xml == '':
			reset_xml = 0
		else:
			reset_xml = int(reset_xml, 16)

		fields_xml = register.find('fields')

		# Attempt to determine register data type
		match size_xml:
			case 64:
				type = 'uint64_t'
			case 32:
				type = 'uint32_t'
			case 16:
				type = 'uint16_t'
			case 8:
				type = 'uint8_t'
			case _:
				type = 'UNKNOWN'

		# Sometimes registers do not have defined fields, add them if they exist
		if fields_xml is not None:
			for field in fields_xml:
				field_name_xml = get_xml_text('name', field)
				field_description_xml = get_xml_text('description', field)

				bitOffset_xml = field.find('bitOffset')
				bitWidth_xml = field.find('bitWidth')

				# Attempt to parse field size
				if bitOffset_xml is not None and bitWidth_xml is not None:
					# bitOffset and bitWidth
					field_offset = bitOffset_xml.text.strip()
					field_width = bitWidth_xml.text.strip()
				else:
					# bitRange
					bitRange_xml = field.find('bitRange')

					if bitRange_xml is None:
						print(f'Failed to load SVD: Offset and Width for {peripheral_name}.{name}.{field_name}')
						return []

					# Bit Range is in the format: [<lsb>:<msb>]
					m = re.match(r'\[(\d+):(\d+)\]', bitRange_xml.text.strip())

					if len(m.groups()) < 2:
						print(f'Failed to load SVD: Invalid BitRange {peripheral_name}.{name}.{field_name}')
						return []

					# Parse out offset and width using LSB and MSB
					field_offset = int(m[1])
					field_width = int(m[2]) - int(m[1]) + 1

				access_xml = field.find('access')
				readonly = False

				if access_xml is not None:
					if access_xml.text.strip() == 'read-only':
						readonly = True

				fields.append(Field(
					field_name_xml,
					field_description_xml,
					int(field_offset),
					int(field_width),
					readonly
				))

		# If there are fields present,
		if len(fields) > 0:
			# Ensure fields are sorted by offset
			fields.sort()

			# Check to see if the first field starts at bit 0
			if len(fields) > 0 and fields[0].offset != 0:
				start_next = fields[0].offset

				# Add a reserved section from bit 0 to the start of the next field
				fields.insert(0, Field('', 'Reserved', 0, start_next - 1, True))

				if verbose > 1:
					print(f'  └> {name_xml}: Reserved field added at offset 0: {start_next - 1}')

			# Check for gaps between fields
			for i in range(len(fields) - 1):
				start = fields[i].offset
				end = start + fields[i].width

				start_next = fields[i + 1].offset
				diff = start_next - end

				# If there is a gap, add a Reserved section
				if diff > 0:
					fields.append(Field('', 'Reserved', end, diff, True))

					if verbose > 1:
						print(f'  └> {name_xml}: Reserved field added at offset {end}: {diff}')

			# Re-sort after adding necessary reserved sections
			fields.sort()

			# Check to see if the last field ends at bit 31
			if fields[-1].offset + fields[-1].width != 32:
				start = fields[-1].offset
				end = start + fields[-1].width

				# Add a reserved section from the next bit after the last field to bit 31
				fields.append(Field('', 'Reserved', end, 32 - end, True))

				if verbose > 1:
					print(f'  └> {name_xml}: Reserved field added at offset {end}: {32 - end}')

		# Append register
		output.append(Register(size_xml, offset_xml, name_xml, description_xml, type, fields, reset=reset_xml))

	# Return parsed registers
	return output

def main():
	parser = argparse.ArgumentParser()

	parser.add_argument('-v', '--verbose', help='Output extra information when parsing', action="count", default=0)
	parser.add_argument('-f', '--file', help='Input SVD file to parse', type=str, action="store", default='')
	parser.add_argument('-o', '--output', help='Output directory for header files', type=str, action="store", default='')
	parser.add_argument('-c', '--create', help='Create Output directory if it does not exist', action="store_true", default=False)
	parser.add_argument('-p', '--prefix', help='Output header file prefix (<prefix>_<peripheral name>.h>', action='store', default='')

	args = parser.parse_args()

	if len(args.file) < 1:
		print('No input file')
		return

	args.file = os.path.abspath(args.file)
	print(f'Opening file {args.file}')

	output = False
	if len(args.output) > 0:
		args.output = os.path.abspath(args.output)

		if not os.path.exists(args.output):
			if args.create == False:
				print(f'Output directory {os.path.abspath(args.output)} does not exist, exiting')
				return
			else:
				print(f'Creating output directory {os.path.abspath(args.output)}')
				os.mkdir(args.output)
				output = True
		else:
			if not os.path.isdir(args.output):
				print(f'Output path exists but is not a directory, exiting')
				return

			output = True

	try:
		tree = ET.parse(args.file)
	except FileNotFoundError:
		print('Failed to open input file: No such file or directory')
		return
	except IsADirectoryError:
		print('Failed to open input file: Is a Directory')
		return
	except xml.etree.ElementTree.ParseError:
		print('Failed to parse SVD: Invalid XML')
		return

	root_xml = tree.getroot()

	if root_xml is None:
		print('Failed to parse SVD: XML Missing root')
		return

	vendor_xml = root_xml.find('vendorID')
	chip_xml = root_xml.find('name')
	version_xml = root_xml.find('version')

	message = 'Found '

	# Print some SVD information
	if vendor_xml is None and chip_xml is None and version_xml is None:
		message += 'Unknown Chip'
	else:
		if vendor_xml is not None:
			message += vendor_xml.text.strip() + ' '

		if chip_xml is not None:
			message += chip_xml.text.strip() + ' '

			if len(args.prefix) < 1:
				args.prefix = chip_xml.text.strip()

		if version_xml is not None:
			message += 'SVD Version ' + version_xml.text.strip()

	print(message)

	peripherals_xml = root_xml.find('peripherals')

	if peripherals_xml is None:
		print('Failed to load SVD: No peripherals')
		return

	print('Loading peripherals...')
	derived = 0

	peripherals = []
	duplicates = []

	register_count = 0
	field_count = 0

	if args.verbose > 0:
		print('')

	for peripheral_xml in peripherals_xml:
		attrib_xml = peripheral_xml.attrib

		# Skip derived peripherals
		if len(attrib_xml) > 0 and 'derivedFrom' in attrib_xml:
			derived += 1
			continue

		peripheral = load_peripheral(peripheral_xml, args.verbose)

		# Failed to parse a peripheral, skip it
		if peripheral is None:
			continue

		path = os.path.join(args.output, f'{args.prefix}_{peripheral.name.lower()}.h')

		# Search for duplicate peripherals
		duplicate = next((x for x in peripherals if x.name == peripheral.name), None)

		# Ensure duplicates don't have differences
		if duplicate is not None and peripheral != duplicate:
			print(f'Duplicate found for peripheral {peripheral.name} ({duplicate.realname}, {peripheral.realname})')
			path = os.path.join(args.output, f'duplicate/{args.prefix}_{peripheral.realname.lower()}.h')

			directory = os.path.join(args.output, 'duplicate')
			if not os.path.exists(directory):
				os.mkdir(directory)

			duplicates.append([duplicate.path, path])

		peripheral.path = path
		peripherals.append(peripheral)

		if args.verbose > 0:
			print(f'--> {peripheral.name}: {peripheral.description}')
			print(f'  └>{path}')

		# Write header files
		if output == True:
			with open(peripheral.path, 'w') as file:
				file.write(f'#ifndef __{args.prefix.upper()}_{peripheral.name}__\n')
				file.write(f'#define __{args.prefix.upper()}_{peripheral.name}__\n\n')
				file.write('#include <stdint.h>\n\n')

				registers = print_registers(peripheral, args.verbose)

				for register in registers:
					file.write(f'{register}\n')

				file.write(print_peripheral(peripheral, args.verbose))

				file.write('\n\n#endif\n')

			register_count += peripheral.register_count()
			field_count += peripheral.field_count()

	# Generate diff files for duplicate peripherals
	if output == True:
		for duplicate in duplicates:
			with open(duplicate[0]) as file:
				original_text = file.readlines()

			with open(duplicate[1]) as file:
				duplicate_text = file.readlines()

			diff_path = os.path.splitext(duplicate[1])[0] + '.diff'

			with open(diff_path, 'w') as file:
				for line in difflib.unified_diff(original_text, duplicate_text, fromfile=duplicate[0], tofile=duplicate[1], lineterm=''):
					file.write(line)

	print(f'\nFound {len(peripherals)} peripherals with {derived} Derived')
	print(f'Total {register_count} registers with {field_count} fields')

if __name__ == "__main__":
	main()
