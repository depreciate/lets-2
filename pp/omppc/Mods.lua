Mods = createClass()

Mods.parse = function(self, modsFlags)
	if not modsFlags then
		modsFlags = 0
	end

	self.scoreMultiplier = 1
	self.timeRate = 1
	self.overallDifficultyMultiplier = 1

	-- EZ
	if bit32.band(modsFlags, 2) > 0 then
		self.Easy = true
		self.scoreMultiplier = self.scoreMultiplier * 0.5
		self.overallDifficultyMultiplier = 0.5
	end

	-- NF
	if bit32.band(modsFlags, 1) > 0 then
		self.NoFail = true
		self.scoreMultiplier = self.scoreMultiplier * 0.5
	end

	-- HT
	if bit32.band(modsFlags, 256) > 0 then
		self.HalfTime = true
		self.scoreMultiplier = self.scoreMultiplier * 0.5
		self.timeRate = 3/4
	end

	-- DT
	if bit32.band(modsFlags, 64) > 0 then
		print("peepee")
		self.DoubleTime = true
		self.timeRate = 3/2
	end

	return self
end