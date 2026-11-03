use strict;
use warnings;
use POSIX qw(floor ceil);

package PyRandom;
sub new {
  my ($class, $seed) = @_;
  my $self = bless {}, $class;
  $self->{mt} = [(0) x 624];
  $self->{index} = 624;
  $self->seed($seed);
  return $self;
}
sub _u32 { return $_[0] & 0xffffffff; }
sub seed {
  my ($self, $seed) = @_;
  my @key;
  my $n = $seed;
  if ($n == 0) { @key = (0); }
  else {
    while ($n > 0) {
      push @key, $n & 0xffffffff;
      $n = int($n / 4294967296);
    }
  }
  $self->_init_by_array(\@key);
}
sub _init_genrand {
  my ($self, $s) = @_;
  $self->{mt}[0] = _u32($s);
  for my $i (1..623) {
    $self->{mt}[$i] = _u32(1812433253 * ($self->{mt}[$i-1] ^ ($self->{mt}[$i-1] >> 30)) + $i);
  }
  $self->{index} = 624;
}
sub _init_by_array {
  my ($self, $init_key) = @_;
  my $key_length = scalar(@$init_key);
  $self->_init_genrand(19650218);
  my ($i,$j) = (1,0);
  my $k = 624 > $key_length ? 624 : $key_length;
  while ($k--) {
    $self->{mt}[$i] = _u32(($self->{mt}[$i] ^ (($self->{mt}[$i-1] ^ ($self->{mt}[$i-1] >> 30)) * 1664525)) + $init_key->[$j] + $j);
    $i++; $j++;
    if ($i >= 624) { $self->{mt}[0] = $self->{mt}[623]; $i = 1; }
    if ($j >= $key_length) { $j = 0; }
  }
  $k = 623;
  while ($k--) {
    $self->{mt}[$i] = _u32(($self->{mt}[$i] ^ (($self->{mt}[$i-1] ^ ($self->{mt}[$i-1] >> 30)) * 1566083941)) - $i);
    $i++;
    if ($i >= 624) { $self->{mt}[0] = $self->{mt}[623]; $i = 1; }
  }
  $self->{mt}[0] = 0x80000000;
}
sub _twist {
  my ($self) = @_;
  for my $i (0..623) {
    my $y = ($self->{mt}[$i] & 0x80000000) + ($self->{mt}[($i+1)%624] & 0x7fffffff);
    $self->{mt}[$i] = $self->{mt}[($i+397)%624] ^ ($y >> 1);
    if ($y % 2 != 0) { $self->{mt}[$i] ^= 0x9908b0df; }
    $self->{mt}[$i] = _u32($self->{mt}[$i]);
  }
  $self->{index} = 0;
}
sub _genrand_int32 {
  my ($self) = @_;
  $self->_twist() if $self->{index} >= 624;
  my $y = $self->{mt}[ $self->{index}++ ];
  $y ^= ($y >> 11);
  $y ^= (($y << 7) & 0x9d2c5680);
  $y ^= (($y << 15) & 0xefc60000);
  $y ^= ($y >> 18);
  return _u32($y);
}
sub getrandbits {
  my ($self, $k) = @_;
  die "number of bits must be non-negative" if $k < 0;
  return 0 if $k == 0;
  if ($k <= 32) {
    my $r = $self->_genrand_int32();
    return $r >> (32 - $k);
  }
  my $words = int(($k - 1) / 32) + 1;
  my $acc = 0;
  my $shift = 0;
  for (my $i = 0; $i < $words; $i++) {
    my $r = $self->_genrand_int32();
    if ($i == $words - 1) {
      my $rem = $k - 32 * $i;
      $r >>= (32 - $rem) if $rem < 32;
    }
    $acc |= ($r << $shift);
    $shift += 32;
  }
  return $acc;
}

sub _randbelow {
  my ($self, $n) = @_;
  my $k = 0;
  my $m = $n - 1;
  while ($m > 0) { $k++; $m >>= 1; }
  while (1) {
    my $r = $self->getrandbits($k);
    return $r if $r < $n;
  }
}
sub randrange_inclusive {
  my ($self, $a, $b) = @_;
  return $a + $self->_randbelow($b - $a + 1);
}
sub choice_idx {
  my ($self, $n) = @_;
  return $self->_randbelow($n);
}
sub random {
  my ($self) = @_;
  my $a = $self->_genrand_int32() >> 5;
  my $b = $self->_genrand_int32() >> 6;
  return ($a * 67108864.0 + $b) / 9007199254740992.0;
}
sub sample_indices {
  my ($self, $n, $k) = @_;
  my @result;
  my $setsize = 21;
  if ($k > 5) {
    my $pow4 = 1;
    while ($pow4 < $k * 3) { $pow4 *= 4; }
    $setsize += $pow4;
  }
  if ($n <= $setsize) {
    my @pool = (0..$n-1);
    for my $i (0..$k-1) {
      my $j = $self->_randbelow($n - $i);
      $result[$i] = $pool[$j];
      $pool[$j] = $pool[$n - $i - 1];
    }
  } else {
    my %selected;
    for my $i (0..$k-1) {
      my $j = $self->_randbelow($n);
      while (exists $selected{$j}) {
        $j = $self->_randbelow($n);
      }
      $selected{$j} = 1;
      $result[$i] = $j;
    }
  }
  return @result;
}

package main;

sub count_words {
  my ($path) = @_;
  open my $fh, '<', $path or die $!;
  my $in = 0;
  my $count = 0;
  while (my $line = <$fh>) {
    if ($line =~ /word_list\s*=\s*\(/) { $in = 1; next; }
    last if $in && $line =~ /^\s*\)/;
    if ($in) {
      while ($line =~ /"([^"]*)"/g) { $count++; }
    }
  }
  close $fh;
  return $count;
}

my $N = count_words('/testbed/faker/providers/lorem/en_US/__init__.py');
my @letters = split //, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
my $r = PyRandom->new(424242);

sub pystr20 {
  my ($r) = @_;
  my $s = '';
  for (1..20) {
    my $idx = floor($r->random() * 52.0);
    $s .= $letters[$idx];
  }
  return $s;
}
sub pyint_0_9999 { my ($r)=@_; return $r->randrange_inclusive(0,9999); }
sub pyfloat_default {
  my ($r)=@_;
  my $right = $r->randrange_inclusive(1,14);
  my $left_digits = 15 - $right; $left_digits = 1 if $left_digits < 1;
  my $sign = $r->choice_idx(2) == 0 ? '+' : '-';
  my $left = $r->randrange_inclusive(0, (10**$left_digits)-1);
  my $frac = $r->randrange_inclusive(0, (10**$right)-1);
  my $str = $sign . $left . '.' . $frac;
  my $num = 0 + $str;
  if ($right) {
    my $max = (10**$left_digits) - (10 ** ( -$right));
    my $min = -(10**$left_digits + (10 ** ( -$right)));
    $num = $max if $num > $max;
    $num = $min if $num < $min;
  } else {
    my $max = (10**$left_digits) - 1;
    my $min = -(10**$left_digits + 1);
    $num = $max if $num > $max;
    $num = $min if $num < $min;
  }
  return $num;
}
sub random_type {
  my ($r, $types_ref) = @_;
  my @types = @{$types_ref};
  my $t = $types[$r->choice_idx(scalar(@types))];
  return pystr20($r) if $t eq q{str};
  return pyint_0_9999($r) if $t eq q{int};
  return pyfloat_default($r);
}


for my $iter (1..3) {
  $r->choice_idx($N);  # generator.word()
  random_type($r, [q{str},q{int},q{float}]);     # d[word]
  random_type($r, [q{str},q{int},q{float}]);     # types append
  $r->choice_idx($N);  # generator.word()
  for (1..8) { random_type($r, [q{str},q{int},q{float}]); }
}

my $pct = $r->randrange_inclusive(60,140);
my $nb = int(4 * $pct / 100);
$nb = 1 if $nb < 1;
my @sample = $r->sample_indices($N, $nb);
my @vals;
for (1..$nb) { push @vals, random_type($r, [q{int},q{str},q{float}]); }
print "N=$N nb=$nb pct=$pct\n";
for my $v (@vals) {
  if (!defined $v) { print "undef\n"; }
  else { print "$v\n"; }
}
