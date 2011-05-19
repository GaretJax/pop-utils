$source = "http://cloud.github.com/downloads/GaretJax/pop-linker/pop-linker_0.3b.tar.gz"

exec { "get-sources":
	command => "curl ${source} | tar xz",
	before => Exec['build'],
	cwd => "/root",
	unless => "/usr/bin/which pop-link",
	path => ['/bin', '/usr/bin']
}

exec { "build":
	command => "make ; make install",
	cwd => "/root/linker",
	path => ['/bin', '/usr/bin', '/usr/local/popc/bin'],
	before => File["/root/linker"],
}

file { "/root/linker":
	ensure => absent,
	force => true,
}
