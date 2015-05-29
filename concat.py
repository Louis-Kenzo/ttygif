#!/usr/bin/env python
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK

import sys

class RelativeFrame:
	def __init__(self, filename, delay):
		self.filename  = filename
		self.delay     = delay

class SampleFrame:
	def __init__(self, filename, sample_number, sample_distance):
		self.filename        = filename
		self.sample_number   = sample_number
		self.sample_distance = sample_distance

class RelativeFrameSequence:
	def __init__(self, sorted_frames):
		self.sorted_frames = sorted_frames

	def subsample(self, fps):
		sampled_frames = []
		current_frame_us = 0
		last_sample_distance_us = 0
		sampling_period_us = 1e6 / fps
		sampling_radius_us = sampling_period_us / 2

		for frame in self.sorted_frames:
			current_frame_us += frame.delay
			# We add sampling_radius_us so that the first frame is centered on time 0
			sample_frame_number = int((current_frame_us+sampling_radius_us) / sampling_period_us)
			sample_frame_location = sample_frame_number*sampling_period_us
			sample_distance = current_frame_us - sample_frame_location
			sampled_frame = SampleFrame(frame.filename, sample_frame_number, sample_distance)

			if not sampled_frames or sample_frame_number != sampled_frames[-1].sample_number:
				sampled_frames.append(sampled_frame)
			else:
				if abs(sampled_frame.sample_distance) < abs(sampled_frames[-1].sample_distance):
					sampled_frames[-1] = sampled_frame

		return sampled_frames

	def subsampleGIF(self, fps):
		period_ms = 1e2 / fps
		sampled_frames = self.subsample(fps)
		sample_gaps = [j.sample_number-i.sample_number
		               for i, j in zip(sampled_frames[:-1], sampled_frames[1:])]
		GIF_frame_names = [f.filename for f in sampled_frames]
		GIF_frame_delays = [int(d*period_ms) for d in [0] + sample_gaps]

		return [RelativeFrame(f,d) for f,d in zip(GIF_frame_names,GIF_frame_delays)]

# –––
# CLI

def CLI(args):
	if args.fps > 66:
		print "Warning: FPS above 66 imply GIF delays of less than 15ms, which may cause slow replay"

	# ––––––––––––––––––––––––––––––––––––
	# Parse files in the current directory

	if not args.inputs:
		import glob
		input_files = glob.glob("*.xwd")
	else:
		input_files = args.inputs

	if not input_files:
		sys.exit("No input file")

	import re
	parsed_filenames = []
	last_order = None
	for f in input_files:
		m = re.match(r"^(\d+)_(\d+)\.[a-zA-Z]+$", f)
		if m:
			order = int(m.group(1))
			delay = int(m.group(2))
			parsed_filenames.append((order, f, delay))

	from operator import itemgetter
	order_sorted_parsed_filenames = sorted(parsed_filenames, key = itemgetter(0))

	valid_set = True
	for pf1, pf2 in zip(order_sorted_parsed_filenames[:-1], order_sorted_parsed_filenames[1:]):
		if pf2[0] != pf1[0]+1:
			valid_set = False
			print "Warning: file " + pf2[1] + " isn't immediately consecutive to " + pf1[1]

	# –––––––––––––––––––––––––
	# Build a sequence of files

	sequence = RelativeFrameSequence([RelativeFrame(pf[1],100*pf[2])
	                                  for pf in order_sorted_parsed_filenames])

	# –––––––––––––––––––––––––––––––––––––––––––––––
	# Sample the GIF and generate the convert command

	import copy
	GIF_frames = sequence.subsampleGIF(fps=args.fps)
	# Add a terminal pausing frame
	GIF_frames.append(copy.deepcopy(GIF_frames[-1]))
	GIF_frames[-1].delay = args.pause * 100
	# Generate frame specifications for the convert command
	GIF_frame_specs = [GIF_frames[0].filename] \
	                + ["-delay {} {}".format(f.delay, f.filename) for f in GIF_frames[1:]]


	convert_command_format = "convert {frame_specs} -layers Optimize -loop 0 {output}"
	convert_command = convert_command_format.format(output = args.output,
		                                            frame_specs = " ".join(GIF_frame_specs))
	print convert_command

	# ––––––––––––––––––––––
	# Execute the conversion

	import subprocess
	import os

	return_code = subprocess.call(convert_command.split())
	if return_code != 0:
		sys.exit("Failed to convert images to GIF")
	else:
		if args.delete and valid_set:
			for f in input_files:
			    os.remove(f)
		print "Successfully generated gif " + args.output + " sampled at " + str(args.fps) + " FPS"

# –––––––––––––––––
# Parser definition

import argparse

main_parser = argparse.ArgumentParser(description="Transform a set of ttygif images into a GIF",
	                                  formatter_class=argparse.ArgumentDefaultsHelpFormatter)
main_parser.add_argument("inputs", nargs="*", help="Input files")
main_parser.add_argument("--output", "-o", default="out.gif", help="Name of the output GIF file")
main_parser.add_argument("--fps",   type=float, default=25, help="Sampling FPS")
main_parser.add_argument("--pause", type=float, default=2,  help="Pause in seconds at the end of the GIF")
main_parser.add_argument("--loop",  type=int,   default=0,  help="Number of GIF loops (0 is infinite)")
main_parser.add_argument("--delete", "-d", action="store_true",  help="Delete inputs when done")
main_parser.set_defaults(func = CLI)

# –––––––––––––––
# Auto-completion

try:
	import argcomplete
	has_argcomplete = True
except ImportError:
	has_argcomplete = False

if has_argcomplete:
	argcomplete.autocomplete(main_parser)

# ––––––––––––
# Rune the CLI

parsed_arguments = main_parser.parse_args(sys.argv[1:])
parsed_arguments.func(parsed_arguments)

